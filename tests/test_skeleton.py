"""Walking-skeleton tests (F-01).

Cover the two contracts the skeleton introduces — the ObservationEvent emitter
funnel and the signed-cookie session round-trip — plus the end-to-end path
(select sample -> greeting + observation events over SSE) with the Claude call
stubbed so the test is deterministic and needs no API key.
"""

from __future__ import annotations

import app.agent.graph as graph_module
from app.observability.events import ObservationEmitter, ObservationEvent
from app.session import SessionState, deserialize, serialize


# --- ObservationEvent emitter funnel (ADR-004) ---------------------------------

def test_emit_produces_wellformed_event_and_increments_nothing_unexpected():
    emitter = ObservationEmitter()
    emitter.question_count = 2
    ev = emitter.emit("tool_call", "did a thing", ts=123.0, tool="greet", phase="intake")
    assert isinstance(ev, ObservationEvent)
    assert ev.kind == "tool_call"
    assert ev.summary == "did a thing"
    assert ev.tool == "greet"
    assert ev.question_count == 2  # carries the running count
    assert ev.ts == 123.0
    assert ev in emitter.events


def test_emit_fans_out_to_registered_sinks():
    emitter = ObservationEmitter()
    seen = []
    emitter.add_sink(seen.append)
    emitter.emit("decision", "x", ts=1.0)
    assert len(seen) == 1
    assert seen[0].summary == "x"


def test_event_serializes_as_sse_frame():
    ev = ObservationEvent(kind="phase_change", summary="ok", ts=1.0)
    frame = ev.to_sse()
    assert frame.startswith("event: observation\ndata: ")
    assert frame.endswith("\n\n")


# --- Signed-cookie session round-trip (ADR-009) --------------------------------

def test_session_roundtrips():
    state = SessionState(
        messages=[{"role": "assistant", "content": "hi"}],
        w2_source="sample",
        questions_asked=3,
        phase="collecting",
    )
    restored = deserialize(serialize(state))
    assert restored.w2_source == "sample"
    assert restored.questions_asked == 3
    assert restored.phase == "collecting"
    assert restored.messages == [{"role": "assistant", "content": "hi"}]


def test_tampered_cookie_yields_fresh_session():
    good = serialize(SessionState(questions_asked=5))
    tampered = good[:-3] + "xxx"
    restored = deserialize(tampered)
    assert restored.questions_asked == 0  # fresh, not the forged value


def test_missing_cookie_yields_fresh_session():
    restored = deserialize(None)
    assert restored.questions_asked == 0
    assert restored.w2_source is None


# --- End-to-end skeleton path (greeting + events over SSE) ----------------------

def test_stream_emits_observation_events_and_greeting(monkeypatch):
    # Stub the Claude call so the test is deterministic and needs no API key.
    monkeypatch.setattr(graph_module.llm, "greet", lambda wage_hint=None: "Hi there!")

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    # Select the sample W-2 (AC4): proceeds with the sample loaded, no upload.
    resp = client.post("/session/sample")
    assert resp.status_code == 200
    assert resp.json()["source"] == "sample"

    # Stream the agent's run; expect observation events and the greeting (AC16).
    with client.stream("GET", "/stream") as s:
        body = "".join(chunk for chunk in s.iter_text())

    assert "event: observation" in body
    assert "Started the conversation" in body  # phase_change event visible
    assert "event: assistant" in body
    assert "Hi there!" in body
    assert "event: done" in body
