"""FastAPI app: the web chat, the live observation stream, and signed-cookie
session state (ADR-009).

Iteration 01 (walking skeleton): serve a minimal chat page with a live
observation panel; let the user select the bundled sample W-2 (or upload a file,
stored for later extraction); run the LangGraph agent to produce a warm
greeting; and stream every observation event to the UI over SSE. Session state
lives only in a signed cookie — nothing is stored server-side.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from app.agent.graph import AGENT
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
    """Run the agent and stream its observation events over SSE.

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
