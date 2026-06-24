# Feature: Walking skeleton — chat + SSE + cookie state + minimal graph + events

**ID:** F-01 · **Iteration:** 01-skeleton · **Status:** Not started

## What this delivers (before → after)
**Before:** Nothing runs; there is no application.
**After:** A user opens the web chat in a browser, selects the bundled sample W-2 (or uploads a file), receives a warm greeting from the agent, and sees at least one live observation event appear in the observation panel — proving the FastAPI server, the SSE event stream, signed-cookie session state, a minimal LangGraph graph, and the ObservationEvent emitter all work end to end.

## How it fits the roadmap
The first vertical slice of iteration 01. It owns the minimum infrastructure, the three load-bearing contracts (graph state, ObservationEvent, the web/cookie/SSE plumbing), and the bundled-sample fallback. Every later feature extends one axis of it. No hard dependencies — it is the foundation.

## Requirements traced (from the PRD)
R1 (stateful chat), R3 (bundled sample fallback), R16 (observable behavior, live in UI), R20 (fake-data/no-PII via cookie-only state), R18/R19 partial (a runnable app). Acceptance: AC4 (sample fallback), partial AC1/AC16.

## Dependencies (must exist before this starts)
- None — can start as soon as the iteration's contracts are frozen.
- External: an Anthropic API key in `.env` (used minimally here for the greeting; required for later features). See Manual setup.

## Unblocks (what waits on this)
- F-02 (W-2 extraction) — consumes the graph + event plumbing and the cookie state.
- F-04 (conversation) — extends the graph with the collect loop.
- F-08 (tax-trace panel) — consumes the observation/UI surface.
- F-06 (deploy) — deploys this app.

## Contracts touched
- **Agent graph state** (source of truth: ADR-001) — introduces the minimum-viable `TypedDict`: `messages`, `w2_data` (None here), `answers` (empty), `questions_asked: 0`, `phase` (`"intake"`), `events`. Later features add fields/phases.
- **ObservationEvent** (source of truth: ADR-004) — introduces the event schema + the single `emit()` funnel and wires it to both the structured logger and the SSE stream. Extended by every later feature.
- **Web/cookie/SSE plumbing** (source of truth: ADR-009) — introduces FastAPI serving the minimal page, the SSE `StreamingResponse` with typed JSON events, and signed `HttpOnly/Secure/SameSite=Strict` cookie session state (no server-side store).

## Acceptance criteria (product behavior)
1. Opening the served page in a browser shows a usable chat interface that accepts input, with no authentication (partial AC1).
2. A one-click "use the sample W-2" control loads the bundled sample into session state and the agent proceeds with a warm greeting, no upload required (AC4).
3. A file-upload control accepts a PDF/image and stores it for extraction (extraction itself is F-02); selecting the sample and uploading are both available.
4. At least one ObservationEvent (e.g. a `phase_change` to intake, or the greeting turn) appears in the live observation panel via SSE, showing its kind and the current `question_count` = 0 (partial AC16).
5. Session state (messages, sample-or-upload selection, counter) round-trips across a turn via the signed cookie; no session data is written server-side (supports R20/AC18).
6. The agent's greeting is warm and plain-language (partial AC17) and states it is an educational tool, not tax advice (partial AC14 framing).

## Testing requirements
- Unit: the `emit()` funnel produces well-formed ObservationEvents for each `kind`; cookie session encode/decode round-trips and rejects a tampered cookie.
- Integration: a request cycle (load page → select sample → receive SSE greeting event) drives the graph and streams at least one typed event; an injected exception mid-stream surfaces as a typed `error` SSE event, not an HTTP status change.
- Contract: the graph state and ObservationEvent shapes match the frozen signatures.

## Manual setup required
- Provide an Anthropic API key as an environment variable in `.env` (already present in the repo root; confirm it is gitignored and valid). The key is the one required secret.

## Implementation notes (filled in by the building agent)

**Outcome (2026-06-24): Shipped, verified locally on `main`.**

- Stack as designed: Python + FastAPI + LangGraph + Anthropic Claude (`claude-opus-4-8`), SSE transport, signed-cookie session (itsdangerous).
- Files: `app/observability/events.py` (ObservationEvent + emitter funnel, ADR-004), `app/session.py` (signed-cookie state, ADR-009), `app/agent/state.py` + `app/agent/graph.py` + `app/agent/llm.py` (LangGraph agent, ADR-001/003), `app/main.py` (routes + SSE + UI), `app/static/index.html` (chat + live observation panel), `app/sample_w2.py` (bundled-sample figures). Scaffolding: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.gitignore`, `.env.example`, `README.md`.
- Verified: `docker compose up` path documented; `pip install -e .` + uvicorn run confirmed; 7 unit/integration tests pass (emitter funnel, cookie round-trip incl. tamper/missing, end-to-end SSE with stubbed LLM). Live run confirmed the full path graph→Claude→ObservationEvent→SSE→client: warm greeting referencing the sample's $44,629 wage, educational-tool framing, each step a structured event with question_count 0/5. Upload boundary rejects non-PDF/image (415) and oversized files (413).
- AC status: AC4 (sample fallback) ✅; partial AC1/AC16/AC17/AC14-framing ✅. Full AC1 (public URL) deferred to F-06.
- Decisions/assumptions for downstream: (1) The skeleton's sample figures live in `app/sample_w2.py` as known constants; F-02 replaces this with real pdfplumber→Vision extraction and the sample becomes the fallback. (2) An *upload* currently reuses the sample figures so the greeting path works pre-extraction — F-02 must wire the real extractor into `/session/upload`. (3) Cookie `secure=False` for localhost; F-06 must set it `True` behind HTTPS. (4) The greeting is a one-shot `messages.create` in `llm.py`; F-04 turns the graph into the multi-node collect loop with the code-enforced budget/guardrails (ADR-002) — the single `intake` node and its `END` edge are the seam to extend.
