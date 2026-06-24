# Roadmap — Agentic Tax-Filing Assistant (OntoIt)

**Status:** draft · **Date:** 2026-06-24
**Source:** [ARCHITECTURE.md](./ARCHITECTURE.md) · [PRD.md](./PRD.md) · [research/](./research/)

## Overview

A LangGraph (Python) agent powers a minimal web chat where a person uploads a single ~$40k W-2, answers ≤5 warm questions, and downloads a correct official IRS 2025 Form 1040 — judged primarily as an agentic harness with four enforced, observable pillars. The arc is **skeleton → working local filer → deploy + committed stretch**: a thin end-to-end slice first, then the full correct filing flow, then the public deployment and the two stretch panels. Assumes a single builder/small team and a short (hackathon) horizon; ship target is a live public URL plus one-command local run.

## The iteration arc

- **Iteration 01: Skeleton** — a user can open the web chat, select/upload the bundled sample W-2, receive a warm greeting, and see one live observation event in the UI — exercising FastAPI + SSE + signed-cookie state + a minimal LangGraph graph + the ObservationEvent contract end to end. → [docs/iterations/01-skeleton/](./iterations/01-skeleton/)
- **Iteration 02: Core filing** — a user can have the full ≤5-question conversation and produce a correct, downloadable official 2025 Form 1040 locally, with the question budget and guardrails enforced in code and the computation provably correct. → [docs/iterations/02-core-filing/](./iterations/02-core-filing/)
- **Iteration 03: Deploy & stretch** — the working filer is reachable at a public URL (and runs locally with one command), and the user can correct an earlier answer mid-conversation and see a "show your work" line-by-line tax trace. → [docs/iterations/03-deploy-and-stretch/](./iterations/03-deploy-and-stretch/)

## Features index

| ID | Feature | Iteration | Spec | "Before → After" (one line) | Depends on (hard) |
|----|---------|-----------|------|------------------------------|--------------------|
| F-01 | Walking skeleton (chat + SSE + cookie + graph + events) | 01-skeleton | [01-walking-skeleton.md](./iterations/01-skeleton/01-walking-skeleton.md) | Before: nothing runs. After: open the chat, pick the sample W-2, get a warm greeting + one live observation event. | — |
| F-02 | W-2 extraction (pdfplumber → Vision, validated) | 02-core-filing | [01-w2-extraction.md](./iterations/02-core-filing/01-w2-extraction.md) | Before: the sample is a static file. After: the agent reads Box 1/2/12 from an upload and shows them in the trail. | F-01 |
| F-03 | Deterministic tax engine (2025 params + Tax Table) | 02-core-filing | [02-tax-engine.md](./iterations/02-core-filing/02-tax-engine.md) | Before: no tax math. After: `compute_tax` returns a correct TaxResult ($3,227 tax / $4,405 refund for the sample) + a trace. | — |
| F-04 | Conversation + enforced 5-question budget + guardrails | 02-core-filing | [03-conversation-budget.md](./iterations/02-core-filing/03-conversation-budget.md) | Before: a greeting only. After: a warm ≤5-question intake that drives the computation, with the cap + guardrails enforced in code. | F-02, F-03 |
| F-05 | Filled official 1040 PDF (PyMuPDF + bake) | 02-core-filing | [04-filled-1040-pdf.md](./iterations/02-core-filing/04-filled-1040-pdf.md) | Before: results are on-screen only. After: download a completed official IRS 2025 Form 1040 file. | F-03 |
| F-06 | Deploy + one-command local run | 03-deploy-and-stretch | [01-deploy-and-run.md](./iterations/03-deploy-and-stretch/01-deploy-and-run.md) | Before: runs only on the dev machine. After: a judge reaches a public URL; anyone runs it locally with one command. | F-01, F-02, F-03, F-04, F-05 |
| F-07 | Mid-conversation answer correction (stretch) | 03-deploy-and-stretch | [02-mid-conversation-correction.md](./iterations/03-deploy-and-stretch/02-mid-conversation-correction.md) | Before: answers are final. After: the user changes status/dependents and the refund recomputes live, no question spent. | F-03, F-04 |
| F-08 | "Show your work" tax-trace panel (stretch) | 03-deploy-and-stretch | [03-tax-trace-panel.md](./iterations/03-deploy-and-stretch/03-tax-trace-panel.md) | Before: just a refund number. After: a line-by-line 1040 with reasons (e.g. "Saver's $0 because AGI > $39,500"). | F-01, F-03 |

**Note on F-02 ⟂ F-03:** within iteration 02, F-02 (extraction) and F-03 (tax engine) have no hard dependency on each other — the engine consumes the frozen `W2`/`TaxResult` contracts, not F-02's runtime output — so they build concurrently. F-04 waits on both; F-05 waits only on F-03. (Do not add an "F-03 after F-02" edge: it is a contract-mediated soft dep, and recording it would needlessly serialize the build.)

## Cross-cutting contracts

| Contract | Source of truth (ADR) | Introduced by | Extended by |
|----------|------------------------|---------------|-------------|
| Agent graph state (`app/agent/state.py`) — `TypedDict` every node reads/writes; edges branch on `questions_asked`/`phase` | [ADR-001](./adrs/ADR-001-langgraph-agent-harness.md) | F-01 | F-02, F-04, F-07 |
| ObservationEvent (`app/observability/events.py`) — the one event shape the UI, logs, and SSE stream consume | [ADR-004](./adrs/ADR-004-observation-event-contract.md) | F-01 | F-02, F-03, F-04, F-05, F-07, F-08 |
| TaxResult / W2 / Answers (`app/tax/types.py`) — computed-return + input value objects | [ADR-006](./adrs/ADR-006-deterministic-tax-engine.md) | F-03 | F-02 (W2), F-04 (Answers), F-05, F-08 |
| 2025 tax parameters + IRS Tax Table (`app/tax/params_2025.py`) — single home of every 2025 figure | [ADR-007](./adrs/ADR-007-tax-parameters-2025.md) | F-03 | — |
| 1040 field map (`app/pdf/field_map.py`) — logical line → AcroForm field name | [ADR-005](./adrs/ADR-005-pdf-filling-pymupdf-bake.md) | F-05 | — |

These are exactly what `kmaz-plan-iteration` freezes with concrete signatures before the build. The first three are introduced in iteration 01–02 and are the load-bearing ones; the planner freezes the full set (additive) at the iteration-02 barrier so F-02/F-03/F-04/F-05 build against stable shapes.

## Risk-weighted ordering

- **Highest risk — tax correctness (F-03).** The PRD's top risk (R-1); the 2025 figures were wrong in the brief. De-risked early in iteration 02 as a standalone, unit-proven feature with a golden test ($3,227/$4,405) before anything consumes it.
- **Second — the PDF fill (F-05).** IRS AcroForm field names are undiscovered and the form has XFA/checkbox quirks; the field-enumeration spike happens at the start of F-05. Isolated so a PDF surprise doesn't block the conversation work.
- **Third — extraction reliability (F-02).** Mitigated by the bundled-sample fallback (shipped in F-01) so a bad upload never blocks the demo.
- **Fourth — deploy/host quirks (F-06).** Render spin-down/cold-start; verified against a live deploy in iteration 03, with the keep-alive approach.
- The harness-enforcement core (F-01 plumbing + F-04 budget/guardrails) is exercised from iteration 01 onward, so the highest-weighted judged property is visible early.

## Non-goals and deferred work

Mirrors PRD §4 / ARCHITECTURE non-goals: no itemized deductions; no income beyond a single W-2; no state/local returns; no filing statuses beyond Single and MFJ; no real e-filing or real PII; no tax advice; no UI polish beyond legibility of the chat + observation + trace panels. Deferred: additional filing statuses (HoH/MFS/QSS); richer messy-W-2 recovery; a dedicated prompt-injection classifier; horizontal scale and persistent storage (single-instance by decision, ADR-011).

## Open questions

- None blocking the plan. Three build-time verification tasks carry forward (facts to confirm, not decisions): confirm the OBBBA-derived 2025 figures against published IRS 2025 Form 1040 instructions (F-03); enumerate live IRS 1040 AcroForm field names (F-05); verify Render spin-down timing against a live deploy (F-06).
