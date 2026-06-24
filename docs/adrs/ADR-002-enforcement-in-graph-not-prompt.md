# ADR-002: Enforce the question budget and guardrails in the graph (state/edges/nodes), never in the prompt

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The brief's highest-weighted criterion is whether the guardrails and the ≤5-question budget are *enforced* or *cosmetic*. R4 requires the budget be enforced "by the system's control logic (not solely by prompt instruction)"; R13–R15 require on-task, no-advice/no-filing, and input-validation guardrails. ADR-001 chose LangGraph; this ADR specifies *how* enforcement is realized within it so the build cannot quietly fall back to prompt-only checks.

## Options considered

- **Prompt-only ("please ask at most 5 questions; stay on tax topics").** Trivial, but exactly the cosmetic failure under test; the model can miscount or be jailbroken. Rejected.
- **Enforcement in the graph (chosen).** The counter is graph state; a conditional edge enforces the cap; guardrails and validation are graph nodes that run *before/around* tool execution, independent of the model's cooperation.
- **A separate enforcement service/middleware outside the graph.** Cleaner separation in theory, but redundant for this scope and splits the observation trail across two systems. Over-engineered here.

## Decision

All enforceable harness properties live in the LangGraph graph:

- **Question budget:** `questions_asked` is incremented in graph state whenever the agent emits a user-facing question; a **conditional edge** routes away from the "ask the user" path to the compute path once it reaches 5. The model cannot emit a 6th question because the edge does not lead there.
- **Guardrails (on-task, no-advice/no-filing):** a guardrail node classifies/screens user turns and the agent's intended actions; off-task or advice/e-file requests are intercepted and answered with the bounded refusal, recorded as an observation event.
- **Input validation:** a validation node checks extracted and user-provided values against a schema (wages a positive number, filing status in the allowed set, dependents a non-negative integer) before any value reaches the tax engine; invalid values route back to a re-ask **without** incrementing `questions_asked` for the same item (satisfies R15/AC15).

## Rationale

This makes each pillar a thing a judge can point at in code: the edge that blocks question #6, the node that refuses off-task input, the validator that rejects negative wages. The enforcement does not depend on the model behaving — which is the whole definition of "enforced, not cosmetic." Re-asks not counting against the budget is a deliberate rule so validation never burns a user-facing question (R15).

## Tradeoffs & risks

- **Gave up:** some conversational spontaneity — the agent cannot freely choose to ask a clarifying 6th question even if it would help. Accepted: the 5-question cap is a hard requirement, and the graph honoring it literally is the point.
- **Risk:** distinguishing "a user-facing question" (counts) from "a re-ask/confirmation" (doesn't) needs a crisp rule, or the counter drifts. *Mitigation:* define it in one place — a question increments the counter only when it solicits *new* information; validation re-asks and confirmations of already-known values do not. The rule is unit-tested (AC5, AC15).
- **Revisit if:** the bounded refusal copy or the classification of off-task proves too blunt in testing.

## Consequences for the build

- **Policy:** no business-critical limit may be enforced by prompt text alone. Every guardrail and the budget counter must have a graph node/edge and a unit test asserting it fires (AC5, AC13, AC14, AC15).
- **Policy:** a validation re-ask never increments `questions_asked`. The "what counts as a question" rule lives in one documented function.
- **Policy:** every guardrail/validation interception emits an observation event (ADR-004) so the judge sees the guardrail fire live (AC13, AC14, AC16).
