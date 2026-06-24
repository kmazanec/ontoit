# ADR-009: FastAPI + SSE transport, minimal web chat, signed-cookie session state (no server-side store)

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The system needs a web chat that carries state across turns (R1) and surfaces the observation trail **live** (R16, AC16), deployed on a free host whose filesystem is ephemeral and which spins down when idle (TECHNOLOGY.md, High confidence). UI polish is explicitly not judged (PRD §4) — the frontend should be minimal and legible. The backend is Python/LangGraph (ADR-001).

## Options considered

- **Transport — WebSocket vs. SSE.** WebSocket is bidirectional but adds reconnection boilerplate and sticky-session scaling concerns for a ~3ms latency edge that is noise against 50–500ms LLM latency. **SSE** is unidirectional server→client (exactly the observation stream), plain HTTP, browser-native reconnect. SSE chosen.
- **State — server-side (in-memory/SQLite/Redis) vs. signed cookie.** On Render free tier all server-side stores reset on spin-down/redeploy, and in-memory Redis is equivalent to a dict for a single instance. A 5-question session (~2–5 KB: messages, W-2 JSON, counter) fits in a **signed cookie**, eliminating server state entirely and surviving spin-down. Cookie chosen.

## Decision

Serve a **minimal web chat** (a single page: chat pane + a live observation panel) from **FastAPI**. Stream agent events to the client via **SSE** (`StreamingResponse`, `text/event-stream`), sending typed JSON events (since the HTTP status cannot change mid-stream, errors are typed events, not status codes). Hold the entire session — message history, extracted W-2 JSON, the `questions_asked` counter — in a **signed, `HttpOnly; Secure; SameSite=Strict` cookie** (or POST body); no server-side session store. POST-initiated SSE uses `fetch()` + `ReadableStream` on the client.

## Rationale

SSE is the smallest correct transport for a one-directional event stream and is what production LLM streaming APIs use. Signed-cookie state makes the app **stateless on the server**, so Render spin-down/redeploy can't corrupt a session, and — because no PII is persisted server-side — it directly supports the fake-data/no-PII guardrail (R20, AC18) and the security posture (ADR-010). Minimal frontend respects the "UI not judged; spend effort on the harness" instruction.

## Tradeoffs & risks

- **Gave up:** server-side session convenience and unbounded session size; the cookie caps how much state we can carry (fine for 5 questions, would not scale to large histories).
- **Risk:** cookie tampering. *Mitigation:* the cookie is signed (integrity-checked) and `HttpOnly/Secure/SameSite=Strict`; the server re-validates extracted values regardless (ADR-002), so a forged cookie still can't bypass the budget or feed bad numbers to the engine.
- **Risk:** SSE error handling if an exception occurs mid-stream. *Mitigation:* typed `error` SSE event, surfaced in the UI.
- **Risk:** cold-start lag mid-demo. *Mitigation:* keep-alive ping during judging (ADR-011).
- **Revisit if:** multi-instance or longer sessions are ever needed (would reintroduce a real session store).

## Consequences for the build

- **Policy:** no PII or session data is persisted server-side; session lives only in the signed cookie. The cookie carries integrity protection and the standard security flags.
- **Policy:** all SSE events are the `ObservationEvent` shape (ADR-004); the observation panel is the SSE consumer. Errors are typed events, never mid-stream status changes.
- **Policy:** the frontend stays minimal (chat + observation panel); no design-system investment.
