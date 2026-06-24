"""Anthropic Claude client (ADR-003).

One provider covers the conversational agent and (later) W-2 vision extraction.
The model id is pinned here, not scattered through the code, so it is changed in
one place. The API key comes from the environment (ANTHROPIC_API_KEY) and is
never logged or committed.

Tone rubric (ADR-002)
---------------------
Every question must:
  1. Acknowledge the user's prior answer (if any) warmly before asking anything
     new — e.g. "Thanks for that!" or "Great, got it."
  2. Be phrased as a friendly, plain-English question, never a form field.
  3. State the reason if not obvious — one short clause is enough.
  4. Keep the total reply to 1–3 sentences.

The `ask_question` helper below encodes this rubric by injecting a prior-answer
acknowledgement into the prompt; tests can assert that the generated question
contains the prior-answer text or verify the rubric via monkeypatching.
"""

from __future__ import annotations

import json

import anthropic

# Pinned model. A current, capable tool-use- and vision-capable Claude model.
MODEL = "claude-opus-4-8"

# The SDK reads ANTHROPIC_API_KEY from the environment. Constructed lazily so the
# app can import without a key present (tests stub the client).
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


SYSTEM_PROMPT = (
    "You are a warm, friendly tax-filing assistant who helps someone file a "
    "simple U.S. federal Form 1040 from a single W-2. You are an educational "
    "tool, not a tax professional, and you never claim to file or e-file the "
    "return. Speak in plain, kind, conversational language — never robotic or "
    "interrogative. Keep replies short."
)

# Canned refusals — fixed text so the guardrail node never calls the LLM for
# off-task turns.  Keeping these as module-level constants makes them unit-
# testable and prevents accidental prompt-only enforcement.

GUARDRAIL_OFF_TASK = (
    "I'm here to help you work through your tax return from your W-2, "
    "so I'll have to skip that one! Let's get back on track — "
    "I just have a couple of quick questions left."
)

GUARDRAIL_NO_FILING = (
    "Just a reminder: I'm an educational helper, not a licensed tax professional, "
    "so I can't file your return or give personalised tax advice. "
    "I can walk you through the numbers so you understand your return, "
    "but you'd want a professional or IRS Free File for the actual submission. "
    "Let's carry on with your figures!"
)


def greet(wage_hint: str | None = None) -> str:
    """Produce a warm opening message. Uses a real Claude call so the skeleton
    proves the full path graph -> Claude -> SSE end to end."""
    client = get_client()
    context = (
        "The user just loaded their W-2. Greet them warmly in 1-2 sentences, "
        "let them know you'll ask only a few quick questions and then prepare "
        "their 2025 Form 1040, and gently note you're an educational helper, "
        "not a tax professional."
    )
    if wage_hint:
        context += f" Their W-2 shows wages of about {wage_hint}."
    message = get_client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def ask_question(
    question_key: str,
    prior_answer_summary: str | None,
    w2_wages_hint: str | None = None,
) -> str:
    """Ask the next question following the tone rubric.

    `question_key` is one of "filing_status" or "dependents".
    `prior_answer_summary` is a plain-English summary of the user's last answer
    (e.g. "Single") — the rubric requires the generated question to acknowledge
    it.  When None (first question) no acknowledgement prefix is emitted.

    This function calls the LLM so tests should monkeypatch it.
    """
    client = get_client()

    ack = (
        f"The user just answered: {prior_answer_summary!r}. "
        "Acknowledge their answer warmly in a few words, then "
    ) if prior_answer_summary else ""

    if question_key == "filing_status":
        prompt = (
            f"{ack}ask the user in one friendly sentence whether they filed as "
            "Single or Married Filing Jointly for 2025. "
            "Do NOT ask any other question."
        )
    elif question_key == "dependents":
        prompt = (
            f"{ack}ask the user in one friendly sentence how many qualifying "
            "children or dependents they have. Zero is a perfectly fine answer. "
            "Do NOT ask any other question."
        )
    else:
        prompt = (
            f"{ack}ask the user for their {question_key} in one friendly sentence."
        )

    if w2_wages_hint:
        prompt += f" (Context: their W-2 shows wages of {w2_wages_hint}.)"

    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _structured(system: str, user: str, schema: dict) -> dict | None:
    """Ask Claude to read a freeform answer and return a value matching `schema`.

    Understanding messy human phrasing is the model's job — so intent parsing
    runs through the LLM with a strict JSON schema, which guarantees the shape of
    what comes back. Returns the parsed object, or None if the call fails (the
    caller then uses an offline heuristic so tests and no-key runs still work)."""
    try:
        message = get_client().messages.create(
            model=MODEL,
            max_tokens=100,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = "".join(b.text for b in message.content if b.type == "text")
        return json.loads(text)
    except Exception:
        return None


def parse_filing_status(user_text: str) -> str | None:
    """Parse a freeform filing-status answer into "single" or "mfj".

    The LLM does the understanding (it handles "me and my spouse", "just me",
    "we file together" — phrasings no keyword list covers); a tiny keyword
    heuristic is the offline fallback. Returns None when truly unrecognisable.
    Tests monkeypatch this to avoid API calls.
    """
    parsed = _structured(
        system=(
            "Read the user's answer about how they file their taxes and classify "
            "it. 'single' covers single/unmarried/head-of-household-style answers; "
            "'mfj' covers married-filing-jointly answers (married, with a spouse, "
            "filing together). Use 'unknown' only if the answer truly doesn't say."
        ),
        user=f"Their answer: {user_text!r}",
        schema={
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["single", "mfj", "unknown"]}},
            "required": ["status"],
            "additionalProperties": False,
        },
    )
    if parsed and parsed.get("status") in ("single", "mfj"):
        return parsed["status"]
    if parsed and parsed.get("status") == "unknown":
        return None

    # Offline fallback (no API / call failed): obvious keywords only.
    lower = user_text.lower().strip()
    if any(w in lower for w in ("single", "unmarried", "just me", "alone")):
        return "single"
    if any(w in lower for w in ("married", "joint", "mfj", "spouse", "together", "we ")):
        return "mfj"
    return None


def parse_dependents(user_text: str) -> int | None:
    """Parse a freeform dependent-count answer into a non-negative int.

    The LLM does the understanding (it handles "just my two", "none of my own",
    "three little ones"); a digit/keyword heuristic is the offline fallback.
    Returns None when no count can be determined. Tests monkeypatch this.
    """
    parsed = _structured(
        system=(
            "Read the user's answer about how many qualifying children / "
            "dependents they have and return the count as a non-negative integer. "
            "Answers like 'none', 'no kids', or 'just me' mean 0. If the answer "
            "doesn't give a number, set count to -1."
        ),
        user=f"Their answer: {user_text!r}",
        schema={
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
            "additionalProperties": False,
        },
    )
    if parsed is not None:
        count = parsed.get("count")
        if isinstance(count, int) and count >= 0:
            return count
        if count == -1:
            return None

    # Offline fallback (no API / call failed). A digit wins first; then worded
    # zeros (checked before "one" so "none" isn't mis-read); then small words.
    import re

    lower = user_text.lower().strip()
    digits = re.search(r"\b(\d+)\b", user_text)
    if digits:
        return int(digits.group(1))
    if any(w in lower for w in ("none", "zero", "no kid", "no children", "no dependent")):
        return 0
    if lower in ("no", "nope", "nah"):
        return 0
    word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for word, value in word_map.items():
        if re.search(rf"\b{word}\b", lower):
            return value
    return None


def present_result(
    refund: str,
    owed: str,
    wages: str,
    filing_status: str,
) -> str:
    """Ask the LLM to present the tax result warmly.  Tests monkeypatch this."""
    client = get_client()
    if refund != "$0":
        outcome = f"they're getting a refund of {refund}"
    else:
        outcome = f"they owe {owed}"

    prompt = (
        f"The user's 2025 federal tax calculation is complete. "
        f"Wages: {wages}, filing status: {filing_status}. "
        f"Result: {outcome}. "
        "Present this in 2-3 warm, plain sentences. "
        "Remind them this is an estimate for educational purposes and they should "
        "use IRS Free File or a professional for the actual submission. "
        "Do NOT invent any other numbers."
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


# Off-task and advice-request detection (guardrail) ----------------------------
# These run BEFORE the LLM so the graph can short-circuit off-task turns without
# ever prompting the model with them.

_OFF_TASK_KEYWORDS = frozenset({
    "poem", "joke", "recipe", "weather", "stock", "sports", "movie", "song",
    "write me", "tell me a story", "what is the meaning",
    "capital of", "translate", "how do i cook", "how do i build",
})

_ADVICE_KEYWORDS = frozenset({
    "file for me", "file this", "file my", "submit my", "e-file", "send it in",
    "pay less tax", "avoid tax", "reduce my tax", "shelter", "offshore",
    "hide income", "what should i do", "how can i pay less",
    "loophole", "not pay", "evade",
})


def classify_user_turn(user_text: str) -> str:
    """Classify the user's message.

    Returns one of:
      "answer"     — looks like a response to a tax question (proceed normally)
      "off_task"   — unrelated topic
      "advice"     — request to file, evade tax, or get personalised tax advice

    Classification is code-only (keyword matching); it never calls the LLM so
    the guardrail is always deterministic and cannot be subverted by rephrasing.
    """
    lower = user_text.lower()
    if any(kw in lower for kw in _ADVICE_KEYWORDS):
        return "advice"
    if any(kw in lower for kw in _OFF_TASK_KEYWORDS):
        return "off_task"
    return "answer"
