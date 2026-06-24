"""The LangGraph agent (ADR-001).

In this iteration the graph is a single intake node: it greets the user (via a
real Claude call) and emits observation events for the phase transition and the
greeting. The point of the skeleton is to prove the whole path — graph state ->
Claude -> ObservationEvent -> SSE -> UI — works end to end. Later iterations add
the extract / validate / collect / compute / fill nodes and the conditional
edges that enforce the question budget and guardrails (ADR-002).

The LLM drives the conversation; the graph carries the enforcement. Keeping the
graph small is deliberate — an over-engineered graph is a real failure mode.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent import llm
from app.agent.state import AgentState


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

    wage_hint = None
    w2 = state.get("w2_data") or {}
    if w2.get("wages"):
        wage_hint = f"${w2['wages']:,.0f}"

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
        "phase": "intake",
    }


def build_graph():
    """Compile the (currently single-node) agent graph."""
    graph = StateGraph(AgentState)
    graph.add_node("intake", intake_node)
    graph.set_entry_point("intake")
    graph.add_edge("intake", END)
    return graph.compile()


# Compiled once at import; the graph definition is static.
AGENT = build_graph()
