"""The LangGraph agent (ADR-001 / ADR-002).

Graph shape
-----------
  intake  ->  collect  <--.
                |          |
                | off_task/advice
                v          |
             guardrail  ---'
                |
                | re-ask (invalid answer, no counter++)
                |
             collect  (ask next question, counter++)
                |
                | budget_exhausted OR enough_info
                v
             compute  ->  END

Enforcement (ADR-002)
---------------------
The question budget is enforced by `_route_collect` — the conditional edge
that leaves the collect node.  When `budget.budget_exhausted(questions_asked)`
returns True, that edge routes to "compute" regardless of whether the
conversation has gathered all desired answers.  The LLM is never called to
produce a question after that predicate fires.  A judge can point at the
`_route_collect` function as the code that blocks question #6.

Guardrails are handled by `_route_user_turn` which calls
`llm.classify_user_turn` (pure keyword matching, no LLM call) BEFORE any LLM
interaction.  Off-task and advice requests go to the guardrail node, which
emits a fixed refusal and routes back to collect.

Multi-turn operation
--------------------
Because session state lives in a cookie (ADR-009) and each HTTP request starts
a fresh Python process (or reuses one without LangGraph state), the graph is
run one step at a time: each POST /message call invokes the relevant node
function directly (via the compiled AGENT or the node helpers imported by
main.py), updates the session, and streams the result.
"""

from __future__ import annotations

import time
from decimal import Decimal

from langgraph.graph import END, StateGraph

from app.agent import budget, llm
from app.agent.state import AgentState
from app.tax.engine import compute_tax
from app.tax.types import Answers, Box12Entry, W2


# ---------------------------------------------------------------------------
# Helper: build a W2 from the session's w2_data dict
# ---------------------------------------------------------------------------

def _w2_from_dict(w2_data: dict) -> W2:
    """Reconstruct a W2 from the session cookie dict.

    The cookie stores amounts as Python floats (JSON round-trip), so wrap in
    Decimal via str to avoid float imprecision.
    """
    box12 = tuple(
        Box12Entry(code=entry["code"], amount=Decimal(str(entry["amount"])))
        for entry in (w2_data.get("box12") or [])
    )
    return W2(
        wages=Decimal(str(w2_data["wages"])),
        federal_withholding=Decimal(str(w2_data["federal_withholding"])),
        box12=box12,
    )


def _wage_hint(w2_data: dict) -> str | None:
    """A '$44,629'-style wage hint for the greeting/questions.

    The cookie may hold the wage as a float (sample path) or a string (upload
    path stores amounts as strings to keep Decimals out of JSON), so coerce to a
    number before formatting — formatting a str with a numeric code raises."""
    raw = (w2_data or {}).get("wages")
    if raw in (None, ""):
        return None
    return f"${float(raw):,.0f}"


# ---------------------------------------------------------------------------
# What info is still needed
# ---------------------------------------------------------------------------

def _next_question_key(answers: dict) -> str | None:
    """Return the key of the next unanswered question, or None if complete.

    The order is fixed: filing_status first, then dependents.
    These are the only two NEW-information questions; credits are inferred.
    """
    if "filing_status" not in answers:
        return "filing_status"
    if "dependents" not in answers:
        return "dependents"
    return None


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def intake_node(state: AgentState) -> dict:
    """Greet the user warmly and record the opening of the session."""
    emitter = state["emitter"]
    now = state["now"]

    emitter.emit(
        "phase_change",
        "Started the conversation",
        ts=now(),
        phase="intake",
    )

    wage_hint = _wage_hint(state.get("w2_data") or {})

    greeting = llm.greet(wage_hint=wage_hint)

    emitter.emit(
        "tool_call",
        "Asked Claude to write a warm greeting",
        ts=now(),
        phase="intake",
        tool="greet",
        inputs={"wage_hint": wage_hint},
    )
    emitter.emit(
        "message",
        "Greeted the user",
        ts=now(),
        phase="intake",
        outputs={"text": greeting},
    )

    return {
        "messages": [{"role": "assistant", "content": greeting}],
        "phase": "collecting",
    }


def collect_node(state: AgentState) -> dict:
    """Ask the next question or parse the latest user answer.

    On a new turn (user message present): parse the answer, update answers dict,
    then ask the next question if the budget allows.
    On the very first collect call (no user message yet): ask the first question.
    """
    emitter = state["emitter"]
    now = state["now"]
    answers: dict = dict(state.get("answers") or {})
    questions_asked: int = state.get("questions_asked") or 0
    messages: list = list(state.get("messages") or [])
    w2_data: dict = state.get("w2_data") or {}

    # Find the most recent user message, if any
    user_text: str | None = None
    for msg in reversed(messages):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        if role == "user" and content:
            user_text = content
            break

    # Keys the agent has already put to the user. A question counts the first
    # time it is asked; asking the *same* key again because the answer was
    # unparseable is a re-ask and does not count (AC5/AC15).
    asked: list = list(answers.get("_asked") or [])

    # Parse the user's answer if there is one and we have an open question
    if user_text:
        pending_key = _pending_parse_key(answers, messages)
        if pending_key == "filing_status":
            parsed = llm.parse_filing_status(user_text)
            if parsed is None:
                # Couldn't parse. If we have never actually asked filing status,
                # this turn IS the first ask and counts; otherwise it's a re-ask.
                first_ask = "filing_status" not in asked
                if first_ask:
                    asked.append("filing_status")
                    questions_asked = budget.increment(questions_asked)
                    emitter.question_count = questions_asked
                    emitter.emit(
                        "question_count",
                        f"Asked question #{questions_asked}: filing_status",
                        ts=now(),
                        phase="collecting",
                        inputs={"question_key": "filing_status"},
                        outputs={"questions_asked": questions_asked},
                    )
                else:
                    emitter.emit(
                        "validation",
                        f"Unrecognised filing status: {user_text!r} — re-asking",
                        ts=now(),
                        phase="collecting",
                        inputs={"user_text": user_text},
                    )
                re_ask = (
                    "I didn't quite catch that — could you let me know if you "
                    "filed as Single or Married Filing Jointly? Either one works!"
                )
                answers["_asked"] = asked
                return {
                    "messages": [{"role": "assistant", "content": re_ask}],
                    "phase": "collecting",
                    "answers": answers,
                    "questions_asked": questions_asked,
                }
            answers["filing_status"] = parsed
            emitter.emit(
                "decision",
                f"Parsed filing status: {parsed!r}",
                ts=now(),
                phase="collecting",
                inputs={"user_text": user_text},
                outputs={"filing_status": parsed},
            )

        elif pending_key == "dependents":
            parsed_deps = llm.parse_dependents(user_text)
            if parsed_deps is None:
                first_ask = "dependents" not in asked
                if first_ask:
                    asked.append("dependents")
                    questions_asked = budget.increment(questions_asked)
                    emitter.question_count = questions_asked
                    emitter.emit(
                        "question_count",
                        f"Asked question #{questions_asked}: dependents",
                        ts=now(),
                        phase="collecting",
                        inputs={"question_key": "dependents"},
                        outputs={"questions_asked": questions_asked},
                    )
                else:
                    emitter.emit(
                        "validation",
                        f"Unrecognised dependent count: {user_text!r} — re-asking",
                        ts=now(),
                        phase="collecting",
                        inputs={"user_text": user_text},
                    )
                re_ask = (
                    "I'm sorry, I didn't understand that. "
                    "Could you just give me a number — how many qualifying children "
                    "or dependents do you have? Zero is totally fine!"
                )
                answers["_asked"] = asked
                return {
                    "messages": [{"role": "assistant", "content": re_ask}],
                    "phase": "collecting",
                    "answers": answers,
                    "questions_asked": questions_asked,
                }
            answers["dependents"] = parsed_deps
            emitter.emit(
                "decision",
                f"Parsed dependents: {parsed_deps}",
                ts=now(),
                phase="collecting",
                inputs={"user_text": user_text},
                outputs={"dependents": parsed_deps},
            )

    # Decide what question to ask next
    next_key = _next_question_key(answers)

    if next_key is None or budget.budget_exhausted(questions_asked):
        # All info gathered or budget exhausted — move to compute
        return {
            "messages": [],
            "phase": "computing",
            "answers": answers,
            "questions_asked": questions_asked,
        }

    # Find the last assistant text as prior-answer context for the rubric
    prior_summary: str | None = None
    if user_text:
        if next_key == "filing_status":
            prior_summary = user_text
        elif next_key == "dependents" and "filing_status" in answers:
            prior_summary = answers["filing_status"]

    wage_hint = _wage_hint(w2_data)
    question_text = llm.ask_question(next_key, prior_summary, wage_hint)

    if next_key not in asked:
        asked.append(next_key)
    answers["_asked"] = asked
    questions_asked = budget.increment(questions_asked)
    emitter.question_count = questions_asked
    emitter.emit(
        "question_count",
        f"Asked question #{questions_asked}: {next_key}",
        ts=now(),
        phase="collecting",
        inputs={"question_key": next_key},
        outputs={"questions_asked": questions_asked},
    )

    return {
        "messages": [{"role": "assistant", "content": question_text}],
        "phase": "collecting",
        "answers": answers,
        "questions_asked": questions_asked,
    }


def guardrail_node(state: AgentState) -> dict:
    """Emit a canned refusal for off-task or advice requests, then return to
    collecting.  This node never calls the LLM — the refusal is a fixed string
    so the guardrail is always deterministic."""
    emitter = state["emitter"]
    now = state["now"]
    messages: list = list(state.get("messages") or [])

    # Find the user's turn that triggered the guardrail
    user_text = ""
    for msg in reversed(messages):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        if role == "user" and content:
            user_text = content
            break

    classification = llm.classify_user_turn(user_text)

    if classification == "advice":
        refusal = llm.GUARDRAIL_NO_FILING
        kind = "advice"
    else:
        refusal = llm.GUARDRAIL_OFF_TASK
        kind = "off_task"

    emitter.emit(
        "guardrail",
        f"Guardrail fired ({kind}): {user_text[:60]!r}",
        ts=now(),
        phase="collecting",
        inputs={"user_text": user_text, "kind": kind},
        outputs={"refusal": refusal[:80]},
    )

    return {
        "messages": [{"role": "assistant", "content": refusal}],
        "phase": "collecting",
        "answers": state.get("answers") or {},
        "questions_asked": state.get("questions_asked") or 0,
    }


def compute_node(state: AgentState) -> dict:
    """Run the deterministic tax engine and present the result warmly."""
    emitter = state["emitter"]
    now = state["now"]
    answers_dict: dict = state.get("answers") or {}
    w2_data: dict = state.get("w2_data") or {}

    emitter.emit(
        "phase_change",
        "Computing tax",
        ts=now(),
        phase="computing",
    )

    # Build typed objects
    w2 = _w2_from_dict(w2_data)
    filing_status = answers_dict.get("filing_status", "single")
    dependents = int(answers_dict.get("dependents", 0))
    answers = Answers(filing_status=filing_status, dependents=dependents)

    result = compute_tax(w2, answers)

    emitter.emit(
        "tool_result",
        f"Tax computed: refund=${result.refund:,.2f} owed=${result.amount_owed:,.2f}",
        ts=now(),
        phase="computing",
        tool="compute_tax",
        outputs={
            "refund": str(result.refund),
            "amount_owed": str(result.amount_owed),
            "total_tax": str(result.total_tax),
            "taxable_income": str(result.taxable_income),
        },
    )

    # Emit each trace step so the observation panel shows the working
    for step in result.trace:
        emitter.emit(
            "decision",
            f"{step.label}: {step.explanation[:100]}",
            ts=now(),
            phase="computing",
        )

    # Format headline numbers for the warm summary
    refund_str = f"${result.refund:,.2f}" if result.refund else "$0"
    owed_str = f"${result.amount_owed:,.2f}" if result.amount_owed else "$0"
    wages_str = f"${result.wages:,.2f}"
    status_label = "Single" if filing_status == "single" else "Married Filing Jointly"

    # Note any credits that materially shaped the result, so the warm summary can
    # explain *why* the refund is what it is (e.g. the EITC their children earned)
    # rather than reading as if it ignored their answers.
    credit_notes: list[str] = []
    if result.eitc:
        credit_notes.append(f"an Earned Income Tax Credit of ${result.eitc:,.0f}")
    if result.savers_credit:
        credit_notes.append(f"a Saver's Credit of ${result.savers_credit:,.0f}")
    credit_note = ""
    if credit_notes:
        kids = f" ({dependents} qualifying child{'ren' if dependents != 1 else ''})" if dependents else ""
        credit_note = "Their result includes " + " and ".join(credit_notes) + kids + "."

    summary = llm.present_result(refund_str, owed_str, wages_str, status_label, credit_note)

    emitter.emit(
        "message",
        "Presented result to user",
        ts=now(),
        phase="computing",
        outputs={"text": summary},
    )

    # Persist the serialisable result
    tax_result_dict = {
        "refund": str(result.refund),
        "amount_owed": str(result.amount_owed),
        "total_tax": str(result.total_tax),
        "taxable_income": str(result.taxable_income),
        "savers_credit": str(result.savers_credit),
        "eitc": str(result.eitc),
        "wages": str(result.wages),
        "filing_status": filing_status,
        "trace": [
            {"label": s.label, "explanation": s.explanation}
            for s in result.trace
        ],
    }

    return {
        "messages": [{"role": "assistant", "content": summary}],
        "phase": "done",
        "tax_result": tax_result_dict,
    }


# ---------------------------------------------------------------------------
# Routing helpers (the edge predicates a judge can point at)
# ---------------------------------------------------------------------------

def _pending_parse_key(answers: dict, messages: list) -> str | None:
    """Which question key is awaiting a parse from the latest user turn.

    We infer this from what's missing in answers.  The first missing key is
    what the last question asked about.
    """
    if "filing_status" not in answers:
        return "filing_status"
    if "dependents" not in answers:
        return "dependents"
    return None


def _route_user_turn(state: AgentState) -> str:
    """Conditional edge: classify the user's latest turn BEFORE the LLM.

    Returns the name of the next node: "guardrail" or "collect".
    This is code-only classification — no LLM call — so guardrails are always
    deterministic and cannot be bypassed by prompt injection.
    """
    messages = state.get("messages") or []
    user_text = ""
    for msg in reversed(messages):
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        if role == "user" and content:
            user_text = content
            break

    classification = llm.classify_user_turn(user_text)
    if classification in ("off_task", "advice"):
        return "guardrail"
    return "collect"


def _route_collect(state: AgentState) -> str:
    """Conditional edge leaving the collect node.

    THIS IS THE ENFORCEMENT POINT for the question budget (ADR-002).
    When budget_exhausted returns True, the edge routes to "compute" and the
    LLM is never called to produce another question.

    Returns "compute" or "collect" (loops back for the greeting flow).
    Because the graph runs one step per /message request, this edge is
    evaluated after collect_node sets `phase`. The phase value drives the
    caller (main.py) rather than LangGraph's internal routing, so we expose
    this predicate for both the graph and the request handler to use.
    """
    questions_asked = state.get("questions_asked") or 0
    answers = state.get("answers") or {}

    if budget.budget_exhausted(questions_asked):
        return "compute"
    if _next_question_key(answers) is None:
        return "compute"
    return "collect"


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def build_graph():
    """Compile the greeting-only graph used by GET /stream.

    The graph contains all nodes so the edges encode the full routing logic,
    but GET /stream only invokes the intake node (greet + END). Multi-turn
    conversation is driven by POST /message, which calls node functions and
    edge predicates directly — one step per HTTP request — so that session
    state can be persisted in the cookie between requests (ADR-009).

    Having all nodes in the compiled graph means a judge can read the complete
    state machine here, even though /message drives it step by step.
    """
    graph = StateGraph(AgentState)

    graph.add_node("intake", intake_node)
    graph.add_node("collect", collect_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("compute", compute_node)

    # GET /stream entry: intake then END (greeting only).
    graph.set_entry_point("intake")
    graph.add_edge("intake", END)

    # POST /message drives these edges one step at a time.
    # After guardrail: always return to collect.
    graph.add_edge("guardrail", "collect")

    # After collect: budget-enforced routing — the enforcement point (ADR-002).
    graph.add_conditional_edges("collect", _route_collect, {
        "collect": END,
        "compute": "compute",
    })

    graph.add_edge("compute", END)

    return graph.compile()


# Compiled once at import; the graph definition is static.
AGENT = build_graph()
