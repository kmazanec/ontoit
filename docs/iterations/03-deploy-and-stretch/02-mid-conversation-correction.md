# Feature: Mid-conversation answer correction (stretch)

**ID:** F-07 · **Iteration:** 03-deploy-and-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** Once an answer is given, it is final; changing filing status or dependents means starting over.
**After:** The user can change an earlier answer ("make it Married Filing Jointly", "I have 1 child") and the agent updates that field, re-runs the deterministic computation, and shows the new refund/owed live — without re-asking answered items and without spending a question.

## How it fits the roadmap
Committed stretch feature; the most tangible demonstration of the stateful chat-loop pillar. Hard-depends on F-04 (the conversation loop it edits) and F-03 (the recompute).

## Requirements traced (from the PRD)
PRD §4 Committed stretch 1; R1 (statefulness). Acceptance: AC19 (mid-conversation correction).

## Dependencies (must exist before this starts)
- **F-04 (conversation + budget)** — HARD dep: extends the collect loop to recognize a correction vs. a new answer.
- **F-03 (tax engine)** — HARD dep: re-runs `compute_tax` on the updated answer.

## Unblocks (what waits on this)
- None.

## Contracts touched
- **Agent graph state** (source of truth: ADR-001) — adds correction handling (update an existing answer field, re-enter compute) without incrementing `questions_asked`.
- **ObservationEvent** (source of truth: ADR-004) — emits an event with old → new value and the recomputed result.

## Acceptance criteria (product behavior)
1. Given a session with answers already given, when the user changes a prior answer (filing status or dependents), then the system updates that field, re-runs the computation, and reflects the new refund/owed (AC19).
2. The correction does **not** re-ask already-answered items and does **not** increment the question counter (AC19, consistent with the AC5 budget rule).
3. A correction that flips eligibility (e.g. MFJ + 1 child) updates the credit result (e.g. EITC from $0 to a correct non-zero), shown with its reason.
4. The change is visible in the observation trail (old → new → recomputed).

## Testing requirements
- Unit: a correction updates the target field and triggers recompute without incrementing the counter; correction vs. new-answer classification is covered.
- Integration: a session that files as Single, then corrects to MFJ-with-1-child, shows the recomputed result and the EITC change.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)
