"""The LangGraph agent's state schema (ADR-001).

This is the shared contract every graph node reads and writes, and the shape the
conditional edges branch on. It mirrors the cookie-backed SessionState but adds
the live, per-invocation handles a node needs while the graph runs — the
ObservationEmitter and a monotonic clock — which are not persisted in the cookie.

Source of truth for the graph-state shape (ADR-001). Later iterations extend
`phase` and add fields; the edge router must handle every `phase` value.
"""

from __future__ import annotations

from typing import Annotated, Any, Callable, Literal, TypedDict

from langgraph.graph.message import add_messages

from app.observability.events import ObservationEmitter

# Every phase the conversation can be in. A new phase must be added here AND
# handled by the edge router — a non-exhaustive `phase` is a build defect.
Phase = Literal[
    "intake",
    "extracting",
    "collecting",
    "computing",
    "filling",
    "done",
]


class AgentState(TypedDict, total=False):
    """State threaded through the graph. `messages` uses LangGraph's reducer so
    nodes append rather than overwrite the chat history."""

    messages: Annotated[list, add_messages]
    w2_source: str | None
    w2_data: dict[str, Any] | None
    answers: dict[str, Any]
    questions_asked: int
    phase: Phase
    tax_result: dict[str, Any] | None

    # Live handles (not persisted to the cookie). `now` returns epoch seconds;
    # injecting it keeps nodes testable and the module import-time deterministic.
    emitter: ObservationEmitter
    now: Callable[[], float]
