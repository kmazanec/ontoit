# ADR-004: A single ObservationEvent schema is the observability contract (fed by LangGraph's stream + explicit domain emits)

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

Observation is a pillar, and the PRD committed to the stretch goal of surfacing the trail **live in the UI**, not just logs (R16, AC16). The judge watches this pillar directly, so it must read as *designed* and show *tax-domain* decisions, not framework plumbing. The decision is the shape of an observation event and how uniformly the system emits it.

## Options considered

- **Lean on LangGraph's native event stream.** Least code and genuinely real, but events are framework-shaped (raw node names, internal payloads) — the judge sees graph plumbing, not "extracted Box 1 = 44,629.35" or "blocked question #6." Less legible.
- **Ad-hoc structured logs per tool/node.** Each emits its own entry; no single schema, so the trail looks assembled and the UI rendering is bespoke per event. Weakest "designed observability" story.
- **One `ObservationEvent` schema, fed by LangGraph + explicit domain emits (chosen).** A single structured event type is the contract; it is populated both from LangGraph's stream (so it is backed by real framework events) and from deliberate domain emissions inside nodes. One shape; the UI, the logs, and the API stream all consume it.

## Decision

Define one `ObservationEvent` type as the observability contract. Every meaningful thing the harness does emits one: tool calls (with inputs/outputs), node/phase transitions, guardrail firings, input-validation rejections, tax decisions, and the running question count. It is populated from LangGraph's event stream where that suffices and from explicit emits inside nodes for domain-meaningful decisions. The UI renders the stream generically; the structured logger writes the same shape.

## Rationale

One schema with three consumers (live UI, logs, API stream) is what makes observability look engineered rather than bolted on — the strongest version of the highest-leverage demo pillar. Backing it with LangGraph's real stream keeps it honest (it is not theater); layering explicit domain emits on top makes it *legible* (the judge sees tax decisions, not graph internals). The judge can watch the Saver's Credit get applied and question #6 get blocked, live — which is exactly the pillar's intent (AC16).

## Tradeoffs & risks

- **Gave up:** the zero-effort path of streaming LangGraph's raw events. We pay a small mapping layer to normalize into our schema.
- **Risk:** double-emitting (once from the framework stream, once explicitly) could duplicate entries. *Mitigation:* a single emitter funnel — framework events are mapped *into* `ObservationEvent` in one place, and nodes call that same emitter for domain events; nothing writes the trail except the funnel.
- **Risk:** over-emitting noise. *Mitigation:* emit at decision granularity (a tool call, a transition, a guardrail, a computed line), not every token.
- **Revisit if:** the transport (ADR-009) needs a different serialization than the in-process schema.

## Consequences for the build

- **Policy:** nothing writes the observation trail except the single emitter funnel; no node logs ad-hoc.
- **Contract consequences (Contract: yes — the observation event shape):**
  - **Source of truth:** `app/observability/events.py` — the `ObservationEvent` model and the `emit()` funnel.
  - **Shape (minimum viable):** `ObservationEvent { id, ts, kind: Literal["tool_call","tool_result","phase_change","guardrail","validation","decision","question_count"], phase, tool: str|None, inputs: dict|None, outputs: dict|None, summary: str (human-readable, e.g. "Applied Saver's Credit 10% = $X"), question_count: int }`.
  - **Exhaustive consumers:** (1) the emitter funnel — the only producer, maps LangGraph events + explicit emits into this shape; (2) the **live UI renderer** — must handle every `kind`; (3) the **structured logger** — serializes every event server-side; (4) the **API/transport layer** (ADR-009) — streams every event to the client. Adding a new `kind` requires updating the UI renderer's switch — a non-exhaustive renderer is a build defect.
