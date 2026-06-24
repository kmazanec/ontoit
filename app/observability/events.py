"""The observability contract: one event shape that the live UI, the structured
logs, and the SSE stream all consume.

Everything the harness does meaningfully — a phase change, a tool call, a
guardrail firing, an input-validation rejection, a computed tax line — funnels
through `emit()` into a single `ObservationEvent`. Nothing writes the trail
except this funnel, so the trail can never look assembled rather than designed,
and a judge sees tax-domain decisions instead of framework plumbing.

Source of truth for the event shape (ADR-004).
"""

from __future__ import annotations

import itertools
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Literal

logger = logging.getLogger("ontoit.observation")

# The kinds of thing the harness reports. The live UI renderer must handle every
# one of these — a new kind without a renderer branch is a build defect.
EventKind = Literal[
    "phase_change",
    "tool_call",
    "tool_result",
    "guardrail",
    "validation",
    "decision",
    "question_count",
    "message",
]

# A monotonic counter gives each event a stable, ordered id within a process.
# (Time is deliberately not used as the id — it is recorded separately as `ts`,
# stamped by the caller — so the module stays import-time deterministic.)
_counter = itertools.count(1)


@dataclass
class ObservationEvent:
    """One inspectable thing the agent did. The same shape reaches the live UI,
    the logs, and the SSE stream."""

    kind: EventKind
    summary: str  # human-readable, e.g. "Applied Saver's Credit 10% = $X"
    phase: str | None = None
    tool: str | None = None
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    question_count: int = 0
    ts: float = 0.0  # epoch seconds, stamped by the caller (kept off the import path)
    id: int = field(default_factory=lambda: next(_counter))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_sse(self) -> str:
        """Serialize as a Server-Sent Event frame. Errors mid-stream are sent as
        typed events, never as an HTTP status change (ADR-009)."""
        return f"event: observation\ndata: {json.dumps(self.to_dict())}\n\n"


# A sink receives every emitted event. The SSE layer registers a per-session
# sink; the logger sink below is always present.
Sink = Callable[[ObservationEvent], None]


def _log_sink(event: ObservationEvent) -> None:
    logger.info(
        "observation",
        extra={"observation": event.to_dict()},
    )


class ObservationEmitter:
    """The single funnel. One per session. Holds the running question count so
    every event carries it, and fans each event out to its registered sinks
    (the live SSE stream and the structured logger)."""

    def __init__(self) -> None:
        self._sinks: list[Sink] = [_log_sink]
        self.question_count: int = 0
        self.events: list[ObservationEvent] = []

    def add_sink(self, sink: Sink) -> None:
        self._sinks.append(sink)

    def remove_sink(self, sink: Sink) -> None:
        if sink in self._sinks:
            self._sinks.remove(sink)

    def emit(
        self,
        kind: EventKind,
        summary: str,
        *,
        ts: float,
        phase: str | None = None,
        tool: str | None = None,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
    ) -> ObservationEvent:
        """Record one observation. The only producer of ObservationEvents."""
        event = ObservationEvent(
            kind=kind,
            summary=summary,
            phase=phase,
            tool=tool,
            inputs=inputs,
            outputs=outputs,
            question_count=self.question_count,
            ts=ts,
        )
        self.events.append(event)
        for sink in list(self._sinks):
            sink(event)
        return event
