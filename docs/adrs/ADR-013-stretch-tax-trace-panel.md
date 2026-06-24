# ADR-013: Stretch — "show your work" tax-trace panel (explained line-by-line computation)

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** yes · **Contract:** no
**Supersedes:** none · **Superseded by:** none

## Context

The judge weights harness quality and provable correctness highly. A stretch feature that renders the 1040 computation line-by-line **with reasoning** turns the deterministic engine (ADR-006) into a visible demo asset and makes correctness self-evidently defensible.

## Options considered

- **Show only the final refund number.** Minimal, but the judge must trust the math is right. Weaker.
- **Line-by-line trace with explanations (chosen).** The engine emits a structured, ordered trace of each step — taxable income, Tax Table lookup, tax, each credit with its eligibility reason, refund — rendered in a panel alongside the chat.

## Decision

The `compute_tax` function returns, alongside `TaxResult`, an ordered **trace**: each step as `(label, value, explanation)` — e.g. "Taxable income = $44,629 wages − $15,750 standard deduction = $28,879"; "Tax = $3,227 (IRS 2025 Tax Table, $28,850–$28,900 row)"; "Saver's Credit = $0 (AGI $44,629 exceeds the $39,500 Single 10% cutoff)"; "EITC = $0 (0 qualifying children; AGI exceeds $19,104 limit)". A UI panel renders the trace. Each trace step is also an ObservationEvent (ADR-004).

## Rationale

It makes the correctness claim inspectable rather than asserted — the judge sees *why* each number is what it is, including why credits are $0, which is exactly the kind of legibility that wins a harness-focused evaluation. It reuses the deterministic engine (the trace is a byproduct of the computation, not a second code path) and the existing observation contract, so it is low-cost. It also doubles as the natural plain-language explanation the agent gives the user (the warm-communication requirement, R17).

## Tradeoffs & risks

- **Gave up:** a little engine surface — `compute_tax` now produces a trace as well as values. *Mitigation:* the trace is generated inline as each line is computed; no duplicate logic. The trace strings are unit-tested against the sample fixture.
- **Risk:** trace text drifting from the actual computed values. *Mitigation:* trace entries are emitted *by* the computation steps that produce the values, not written separately — they cannot diverge without the value diverging.
- **Revisit if:** the trace grows noisy; keep it to the load-bearing lines.

## Consequences for the build

- **Policy:** the trace is produced by the same code path that computes the values (single source of truth); trace and `TaxResult` are asserted together against the golden sample fixture.
- **Policy:** trace steps emit as ObservationEvents and feed both the trace panel and the agent's plain-language explanation.
- **PRD:** reflected back into the PRD as a committed feature.
