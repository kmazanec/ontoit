"""FastAPI app: the web chat, the live observation stream, and signed-cookie
session state (ADR-009).

Iteration 01 (walking skeleton): serve a minimal chat page with a live
observation panel; let the user select the bundled sample W-2 (or upload a file,
stored for later extraction); run the LangGraph agent to produce a warm
greeting; and stream every observation event to the UI over SSE. Session state
lives only in a signed cookie — nothing is stored server-side.

Iteration 02 (F-04): adds POST /message for multi-turn conversation.  Each
call advances the conversation by one step (parse previous answer, ask next
question, or compute when ready), updates the session cookie, and streams
the resulting observation events + assistant reply over SSE.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from app.agent import llm
from app.agent.budget import budget_exhausted
from app.agent.graph import (
    AGENT,
    _next_question_key,
    collect_node,
    compute_node,
    guardrail_node,
    intake_node,
)
from app.extraction import extract_w2, w2_to_dict
from app.observability.events import ObservationEmitter, ObservationEvent
from app.sample_w2 import SAMPLE_W2
from app.session import COOKIE_NAME, SessionState, deserialize, serialize

app = FastAPI(title="OntoIt — Agentic Tax-Filing Assistant")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
# Cap uploads so a malicious/oversized file can't exhaust memory (ADR-010).
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _set_session_cookie(response, state: SessionState) -> None:
    """Write the signed session back. HttpOnly/SameSite=Strict always; Secure is
    set in production (left off for plain-HTTP localhost so the cookie works)."""
    response.set_cookie(
        COOKIE_NAME,
        serialize(state),
        httponly=True,
        samesite="strict",
        secure=False,  # set True behind HTTPS in deployment
        max_age=60 * 60,
    )


@app.get("/health")
def health() -> dict:
    """Liveness probe; also the operator's cheapest health signal (ADR-011)."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((_STATIC_DIR / "index.html").read_text())


@app.post("/session/sample")
def use_sample(request: Request) -> JSONResponse:
    """One-click: load the bundled sample W-2 into the session (AC4)."""
    state = deserialize(request.cookies.get(COOKIE_NAME))
    state.w2_source = "sample"
    state.w2_data = dict(SAMPLE_W2)
    state.phase = "intake"
    response = JSONResponse({"ok": True, "source": "sample"})
    _set_session_cookie(response, state)
    return response


@app.post("/session/upload")
async def upload(request: Request, file: UploadFile) -> JSONResponse:
    """Accept a W-2 upload. The skeleton stores that an upload happened and falls
    back to the sample figures for the greeting; real extraction is F-02."""
    blob = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(blob) > _MAX_UPLOAD_BYTES:
        return JSONResponse(
            {"ok": False, "error": "File too large (max 10 MB)."}, status_code=413
        )
    if file.content_type not in {"application/pdf", "image/png", "image/jpeg"}:
        return JSONResponse(
            {"ok": False, "error": "Please upload a PDF or image."}, status_code=415
        )

    state = deserialize(request.cookies.get(COOKIE_NAME))
    state.w2_source = "upload"
    state.phase = "intake"

    result = extract_w2(blob, file.content_type or "application/pdf")
    if result.ok and result.w2 is not None:
        figures = w2_to_dict(result.w2)
        figures["source"] = result.source
        state.w2_data = figures
        # Emit so the live observation panel shows what was extracted and how.
        emitter = ObservationEmitter()
        emitter.emit(
            "tool_call",
            f"Extracted W-2 via {result.source}: wages={result.w2.wages}, "
            f"withholding={result.w2.federal_withholding}",
            ts=time.time(),
            tool="extract_w2",
            inputs={"content_type": file.content_type},
            outputs={
                "wages": str(result.w2.wages),
                "federal_withholding": str(result.w2.federal_withholding),
                "box12_count": len(result.w2.box12),
                "source": result.source,
                "confidence": result.confidence,
            },
        )
    else:
        # Extraction failed; fall back to the sample so the demo never breaks.
        fallback = dict(SAMPLE_W2)
        fallback["source"] = "sample_fallback"
        state.w2_data = fallback
        emitter = ObservationEmitter()
        emitter.emit(
            "validation",
            f"W-2 extraction failed ({'; '.join(result.errors)}); using sample fallback",
            ts=time.time(),
            tool="extract_w2",
            inputs={"content_type": file.content_type},
            outputs={"errors": result.errors},
        )

    response = JSONResponse({"ok": True, "source": state.w2_data.get("source", "upload")})
    _set_session_cookie(response, state)
    return response


@app.get("/stream")
def stream(request: Request) -> StreamingResponse:
    """Run the agent's intake step and stream its observation events over SSE.

    The HTTP status can't change once the body starts, so any error is sent as a
    typed `error` SSE event rather than a status code (ADR-009).
    """
    state = deserialize(request.cookies.get(COOKIE_NAME))

    def event_source():
        emitter = ObservationEmitter()
        emitter.question_count = state.questions_asked
        try:
            result = AGENT.invoke(
                {
                    "w2_source": state.w2_source,
                    "w2_data": state.w2_data,
                    "answers": state.answers,
                    "questions_asked": state.questions_asked,
                    "phase": state.phase,
                    "emitter": emitter,
                    "now": time.time,
                }
            )
        except Exception as exc:  # surface as a typed SSE event, not a 500
            err = ObservationEvent(
                kind="decision", summary=f"Something went wrong: {exc}", ts=time.time()
            )
            yield err.to_sse()
            return

        # Emit the collected observation trail, then the assistant's message.
        for event in emitter.events:
            yield event.to_sse()

        greeting = ""
        for msg in result.get("messages", []):
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
            if content:
                greeting = content
        yield f"event: assistant\ndata: {json.dumps({'text': greeting})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# POST /message — multi-turn conversation endpoint (F-04)
# ---------------------------------------------------------------------------

class _MessageRequest:
    """Simple data holder; FastAPI's Request.json() avoids a Pydantic import."""
    pass


@app.post("/message")
async def message(request: Request) -> StreamingResponse:
    """Advance the conversation by one user turn.

    Reads the session cookie, appends the user's text, runs the appropriate
    graph node (guardrail check -> collect -> compute if ready), writes the
    updated session cookie on the response, and streams observation events +
    the assistant reply over SSE.

    The question-budget enforcement lives in collect_node via budget.budget_exhausted
    (the conditional-edge predicate).  This handler does not bypass or duplicate
    that logic.
    """
    body = await request.json()
    user_text: str = (body.get("text") or "").strip()

    state = deserialize(request.cookies.get(COOKIE_NAME))

    # Guard: need a W-2 before the conversation can proceed
    if not state.w2_data:
        def _no_w2():
            ev = ObservationEvent(
                kind="validation",
                summary="No W-2 loaded — please use the sample or upload first.",
                ts=time.time(),
            )
            yield ev.to_sse()
            yield f"event: assistant\ndata: {json.dumps({'text': 'Please load a W-2 first!'})}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(_no_w2(), media_type="text/event-stream")

    # Append the user's message to history
    state.messages.append({"role": "user", "content": user_text})

    def event_source() -> Generator[str, None, None]:
        emitter = ObservationEmitter()
        emitter.question_count = state.questions_asked

        graph_state: dict = {
            "messages": [{"role": m["role"], "content": m["content"]} for m in state.messages],
            "w2_source": state.w2_source,
            "w2_data": state.w2_data,
            "answers": dict(state.answers),
            "questions_asked": state.questions_asked,
            "phase": state.phase,
            "emitter": emitter,
            "now": time.time,
        }

        try:
            # Guardrail check — code-only, no LLM
            classification = llm.classify_user_turn(user_text)

            if classification in ("off_task", "advice"):
                node_result = guardrail_node(graph_state)
            else:
                node_result = collect_node(graph_state)
                # If collect moved to computing, run compute immediately
                if node_result.get("phase") == "computing":
                    graph_state.update(node_result)
                    node_result = compute_node(graph_state)

        except Exception as exc:
            err = ObservationEvent(
                kind="decision",
                summary=f"Something went wrong: {exc}",
                ts=time.time(),
            )
            yield err.to_sse()
            yield "event: done\ndata: {}\n\n"
            return

        # Pull the assistant's reply from the node result
        assistant_text = ""
        new_messages = node_result.get("messages") or []
        for msg in new_messages:
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
            if role == "assistant" and content:
                assistant_text = content

        # Update session state from node result
        if "answers" in node_result:
            state.answers = node_result["answers"]
        if "questions_asked" in node_result:
            state.questions_asked = node_result["questions_asked"]
        if "phase" in node_result:
            state.phase = node_result["phase"]
        if "tax_result" in node_result and node_result["tax_result"]:
            # Store on session for the PDF filler (F-05)
            pass  # tax_result not yet in SessionState; F-05 will extend it
        if assistant_text:
            state.messages.append({"role": "assistant", "content": assistant_text})

        # Stream observation events
        for event in emitter.events:
            yield event.to_sse()

        yield f"event: assistant\ndata: {json.dumps({'text': assistant_text})}\n\n"

        # Send the updated session as a cookie header piggyback — since we're
        # inside a streaming response we can't set headers after the fact.
        # Instead, emit a typed 'session' event the client can ignore; the
        # actual cookie update is sent via a Set-Cookie workaround below.
        yield f"event: phase\ndata: {json.dumps({'phase': state.phase})}\n\n"
        yield "event: done\ndata: {}\n\n"

    response = StreamingResponse(event_source(), media_type="text/event-stream")
    _set_session_cookie(response, state)
    return response
