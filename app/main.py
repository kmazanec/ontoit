"""FastAPI app: the web chat, the live observation stream, and signed-cookie
session state (ADR-009).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator

from decimal import Decimal

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

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
from app.pdf.filler import fill_1040
from app.sample_w2 import SAMPLE_W2
from app.session import COOKIE_NAME, SessionState, deserialize, serialize
from app.tax.engine import compute_tax
from app.tax.types import Answers, Box12Entry, W2

_log = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
# Cap uploads so a malicious/oversized file can't exhaust memory (ADR-010).
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Secure-cookie detection (ADR-011 operability)
#
# Render sets RENDER=true automatically in its environment. The app runs
# behind Render's TLS-terminating proxy: the browser connection is HTTPS but
# the app sees plain HTTP — secure=True is still correct because the
# Set-Cookie travels to the browser only over the already-HTTPS outer
# connection. Also honour an explicit COOKIE_SECURE env override so any HTTPS
# host (or local HTTPS reverse-proxy) gets the right behaviour without code
# changes.
# ---------------------------------------------------------------------------
_COOKIE_SECURE: bool = bool(
    os.environ.get("RENDER") or os.environ.get("COOKIE_SECURE", "")
)


def _set_session_cookie(response, state: SessionState) -> None:
    """Write the signed session back. HttpOnly/SameSite=Strict always; Secure
    follows _COOKIE_SECURE (true on Render/HTTPS, false for plain-HTTP local)."""
    response.set_cookie(
        COOKIE_NAME,
        serialize(state),
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        max_age=60 * 60,
    )


# ---------------------------------------------------------------------------
# Keep-alive background task (ADR-011 operability)
#
# Render free-tier services spin down after ~15 min idle (cold starts take
# 30-60 s). When KEEP_ALIVE_URL is set to this service's own /health URL the
# app pings itself every 10 min to prevent spin-down. When the var is unset
# (local dev, CI) the task is skipped entirely — no noise, no extra deps.
# ---------------------------------------------------------------------------
_KEEP_ALIVE_URL: str | None = os.environ.get("KEEP_ALIVE_URL")
_KEEP_ALIVE_INTERVAL = 10 * 60  # seconds


async def _keep_alive_loop() -> None:
    """Periodically GET KEEP_ALIVE_URL to prevent free-tier spin-down."""
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(_KEEP_ALIVE_INTERVAL)
            try:
                await client.get(_KEEP_ALIVE_URL)  # type: ignore[arg-type]
            except Exception as exc:
                _log.debug("keep-alive ping failed (non-fatal): %s", exc)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if _KEEP_ALIVE_URL:
        asyncio.create_task(_keep_alive_loop())
    yield


app = FastAPI(title="OntoIt — Agentic Tax-Filing Assistant", lifespan=_lifespan)


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
# POST /message — multi-turn conversation endpoint
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

    # Advance the conversation SYNCHRONOUSLY, before building the response, so
    # the session mutations (parsed answers, the question counter, the phase)
    # are finalized in `state` when the cookie is written. Doing this work
    # inside the streaming generator would run it lazily, after the cookie had
    # already been serialized from the un-mutated state — losing every answer.
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

    error_summary: str | None = None
    node_result: dict = {}
    try:
        # Guardrail check — code-only, no LLM, outside the model's control.
        classification = llm.classify_user_turn(user_text)
        if classification in ("off_task", "advice"):
            node_result = guardrail_node(graph_state)
        else:
            node_result = collect_node(graph_state)
            # If collect moved to computing, run compute in the same turn.
            if node_result.get("phase") == "computing":
                graph_state.update(node_result)
                node_result = compute_node(graph_state)
    except Exception as exc:  # surface as a typed SSE event, never a 500
        error_summary = f"Something went wrong: {exc}"

    # Pull the assistant's reply and fold the node result into the session.
    assistant_text = ""
    for msg in node_result.get("messages") or []:
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        if role == "assistant" and content:
            assistant_text = content

    if "answers" in node_result:
        state.answers = node_result["answers"]
    if "questions_asked" in node_result:
        state.questions_asked = node_result["questions_asked"]
    if "phase" in node_result:
        state.phase = node_result["phase"]
    if assistant_text:
        state.messages.append({"role": "assistant", "content": assistant_text})

    # The events and reply are now fully determined; the generator only emits.
    collected_events = list(emitter.events)

    def event_source() -> Generator[str, None, None]:
        if error_summary is not None:
            yield ObservationEvent(kind="decision", summary=error_summary, ts=time.time()).to_sse()
            yield "event: done\ndata: {}\n\n"
            return
        for event in collected_events:
            yield event.to_sse()
        yield f"event: assistant\ndata: {json.dumps({'text': assistant_text})}\n\n"
        yield f"event: phase\ndata: {json.dumps({'phase': state.phase})}\n\n"
        yield "event: done\ndata: {}\n\n"

    response = StreamingResponse(event_source(), media_type="text/event-stream")
    _set_session_cookie(response, state)  # state is now finalized
    return response


# ---------------------------------------------------------------------------
# GET /download — the completed, baked official 1040 PDF
# ---------------------------------------------------------------------------

def _session_to_w2_and_answers(state: SessionState) -> tuple[W2, Answers]:
    """Reconstruct W2 + Answers from session cookie data.

    Raises HTTPException(400) when the session lacks the required fields.
    """
    d = state.w2_data
    if not d:
        raise HTTPException(status_code=400, detail="No W-2 data in session.")

    box12 = tuple(
        Box12Entry(str(entry["code"]), Decimal(str(entry["amount"])))
        for entry in d.get("box12", [])
    )
    w2 = W2(
        wages=Decimal(str(d["wages"])),
        federal_withholding=Decimal(str(d["federal_withholding"])),
        box12=box12,
    )

    answers_data = state.answers or {}
    filing_status = answers_data.get("filing_status", "single")
    dependents = int(answers_data.get("dependents", 0))
    answers = Answers(filing_status=filing_status, dependents=dependents)

    return w2, answers


@app.get("/download")
def download_1040(request: Request) -> Response:
    """Return a filled, flattened IRS 2025 Form 1040 PDF for the current session."""
    state = deserialize(request.cookies.get(COOKIE_NAME))
    w2, answers = _session_to_w2_and_answers(state)
    result = compute_tax(w2, answers)
    pdf_bytes = fill_1040(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=form-1040-2025.pdf"},
    )
