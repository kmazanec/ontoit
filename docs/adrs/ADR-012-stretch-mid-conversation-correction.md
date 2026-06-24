# ADR-012: Stretch — mid-conversation answer correction via re-runnable graph state

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** yes · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

A brief stretch goal: let the user correct an answer mid-conversation. The PRD deferred this (PRD §4 Deferred 3). The chosen design — signed-cookie session state (ADR-009) + a LangGraph graph whose computation is a pure tool (ADR-006) — makes it cheap, and it is a strong demonstration of genuine statefulness (a judged property).

## Options considered

- **Restart the session on a correction.** Simple but loses history and feels broken in a demo. Rejected.
- **Re-runnable state update (chosen).** A correction ("make it MFJ", "I have 1 child") updates the relevant field in graph state and re-invokes the deterministic computation; prior W-2 extraction and answers are retained.

## Decision

Support correcting a previously given answer. When the user changes filing status or dependents, the agent updates that field in session state and re-runs `compute_tax`; the conversation continues without re-asking already-answered items. A correction does **not** consume a new question against the budget — it edits an existing answer (consistent with ADR-002's "what counts as a question" rule).

## Rationale

It showcases the harness's stateful chat loop (a judged pillar) in the most tangible way — the judge watches the refund recompute live when they switch to MFJ — and exercises the credits-when-earned path (an MFJ + child correction flips EITC from $0 to non-zero), proving the engine is correct across cases. Cost is low because state is already first-class and the math is a pure, re-callable tool.

## Tradeoffs & risks

- **Gave up:** some conversational simplicity — the agent must recognize a correction vs. a new answer. *Mitigation:* corrections target known fields (status, dependents); the classification is small and testable.
- **Risk:** a correction could interact with the question counter. *Mitigation:* corrections edit existing answers and never increment `questions_asked` (ADR-002 rule); unit-tested.
- **Revisit if:** correction scope expands beyond status/dependents.

## Consequences for the build

- **Policy:** a correction updates state and re-runs the deterministic computation; it never re-asks answered items and never increments the question counter.
- **Policy:** each correction emits an ObservationEvent (old → new value, recomputed result) so the change is visible in the trail.
- **PRD:** reflected back into the PRD as a committed feature (moved out of Deferred).
