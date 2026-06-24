# Feature: Conversation + enforced 5-question budget + guardrails

**ID:** F-04 · **Iteration:** 02-core-filing · **Status:** Not started

## What this delivers (before → after)
**Before:** The agent only greets; it gathers nothing and the budget/guardrails are not enforced.
**After:** The agent conducts a warm, plain-language ≤5-question intake (filing status, dependents, confirm/correct key W-2 figures), drives those answers into the deterministic computation, and enforces the question cap and guardrails **in code** — a judge can point at the graph edge that blocks question #6 and the nodes that refuse off-task/advice requests.

## How it fits the roadmap
The harness's enforcement showcase (the highest-weighted judged property). Hard-depends on F-02 (real extracted values to confirm) and F-03 (calls `compute_tax`).

## Requirements traced (from the PRD)
R4 (5-question budget enforced in code), R5 (essential questions, credits inferred), R13 (on-task), R14 (no-advice/no-filing), R15 (validation re-ask), R17 (warm tone). Acceptance: AC5 (cap enforced), AC10 (no 6th question for credits), AC13 (on-task), AC14 (no-advice/no-filing), AC15 (validation), AC17 (tone).

## Dependencies (must exist before this starts)
- **F-02 (W-2 extraction)** — HARD dep: consumes the extracted values to confirm/correct during the conversation.
- **F-03 (tax engine)** — HARD dep: calls `compute_tax` with the gathered answers to produce and present the result.

## Unblocks (what waits on this)
- F-06 (deploy) — the working filer must exist to deploy.
- F-07 (mid-conversation correction) — extends this conversation loop.

## Contracts touched
- **Agent graph state** (source of truth: ADR-001) — extends with the collect-loop fields and `questions_asked` increments; adds `collecting`/`computing` phases and the conditional edge on `questions_asked >= 5`.
- **TaxResult / W2 / Answers** (source of truth: ADR-006) — extends `Answers` (filing status, dependents). Reconciled with F-03.
- **ObservationEvent** (source of truth: ADR-004) — emits per-turn, guardrail-firing, validation, and question-count events.

## Acceptance criteria (product behavior)
1. Across any complete session the agent asks at most five questions; when a fifth has been asked, the control logic (a graph edge on `questions_asked >= 5`) routes to compute and prevents a sixth — verifiable by the enforced counter, not just observed wording (AC5).
2. Credits (Saver's, EITC) are inferred from W-2 + status + dependents; no question is spent to determine credit eligibility (AC10).
3. An off-topic request (e.g. "write me a poem") is declined and redirected to tax filing, recorded in the trail (AC13).
4. A request for tax advice or to actually file is declined with the educational/no-filing statement, recorded in the trail (AC14).
5. An invalid answer (unrecognized filing status, non-integer dependents) is rejected and re-asked without computing on it and **without** incrementing the question counter for the re-ask (AC15).
6. Each question acknowledges the prior answer and reads as warm, plain-language conversation, not a bare list (AC17, against the tone rubric authored here).
7. After the questions, the agent presents the computed refund/owed in friendly language (consuming F-03's result).

## Testing requirements
- Unit: the counter increments only on a new-information question (not on re-asks/confirmations); the `>= 5` edge blocks a sixth; the "what counts as a question" rule is covered.
- Unit: guardrail nodes fire for off-task and advice/e-file inputs; validation routes re-asks without incrementing.
- Integration: a full sample session (select sample → confirm figures → status → dependents → compute) stays within 5 questions and presents a correct result; injected off-task/advice turns are refused mid-session.
- Tone: a documented tone rubric + at least one assertion that a question acknowledges the prior answer.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)


## Implementation notes (build outcome)

**Shipped on main, verified locally (2026-06-24).**
