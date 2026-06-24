# ADR-006: Tax computation is deterministic, pure, unit-tested code — never the LLM

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The system must produce a **correct** 2025 Form 1040 — exact for the core path plus Saver's Credit and EITC (R6–R10, AC6–AC9, AC11). "Does it actually work" is the second-highest judging criterion. Tax math could be done by the LLM (it can do arithmetic in-context) or by deterministic code the agent calls as a tool.

## Options considered

- **LLM computes the tax in-context.** Zero extra code, but LLMs make arithmetic and table-lookup errors, the result is non-reproducible, and you cannot write a test that asserts the refund equals a hand-computed value. Indefensible for a correctness-critical path. Rejected.
- **Deterministic, pure `compute_tax` function the agent calls as a tool (chosen).** Reproducible, unit-testable against hand-computed expectations, and the LLM never touches the numbers — it only orchestrates and explains them.

## Decision

All tax computation is a **pure, deterministic Python function** — `compute_tax(w2, answers) → TaxResult` — exposed to the agent as a tool (ADR-001/R12). It takes the extracted W-2 figures and the gathered answers, applies the 2025 parameters (ADR-007), and returns every 1040 line value (wages, standard deduction, taxable income, tax, Saver's Credit, EITC, total payments, refund/owed). The LLM calls it and narrates the result; it never performs the arithmetic itself.

## Rationale

This is the only approach under which "it actually works" is *provable*: the acceptance criteria (AC6–AC9, AC11) are written as exact assertions, and a pure function lets the build hand-compute the expected refund for the sample W-2 and assert on it. Determinism also means the same W-2 + answers always yields the same return — a property a judge can verify by re-running. The LLM's strengths (warm phrasing, parsing messy answers) are kept; its weakness (arithmetic) is designed out.

## Tradeoffs & risks

- **Gave up:** nothing of value — the LLM doing math has no upside here.
- **Risk:** the *correctness* now rests entirely on (a) the encoded 2025 parameters (ADR-007) and (b) the function's logic. *Mitigation:* both are unit-tested against the sample W-2's hand-computed return and against the IRS-sourced parameters; the parameters carry citations (R-1).
- **Risk:** edge cases outside the target profile (unusual dependents, ineligibility nuances) could compute a technically-wrong-but-out-of-scope number. *Mitigation:* scope is fixed to the target profile (PRD §4 Out of Scope); the function applies documented simplifying assumptions (e.g. Saver's Credit eligibility per PRD R-4) and the observation trail surfaces them.

## Consequences for the build

- **Policy:** no 1040 line value is ever produced by the LLM. The agent must obtain every number from the `compute_tax` tool. A reviewer finding model-computed arithmetic on the return is a gating defect.
- **Policy:** `compute_tax` is pure (no I/O, no clock, no network) so it is trivially testable; the 2025 parameters are injected, not hardcoded inline, so they can be cited and tested (ADR-007).
- **Contract consequences (Contract: yes — the TaxResult shape):**
  - **Source of truth:** `app/tax/engine.py` (the function) and `app/tax/types.py` (the `TaxResult`/`W2`/`Answers` types).
  - **Shape (minimum viable):** `TaxResult { wages, federal_withholding, agi, standard_deduction, taxable_income, tax_before_credits, savers_credit, eitc, total_credits, total_tax, total_payments, refund, amount_owed, filing_status, lines: dict[str, Decimal] }` — `lines` maps 1040 line numbers to values for the PDF filler. Money is `Decimal`, never float.
  - **Exhaustive consumers:** (1) the `compute_tax` tool/agent; (2) the **PDF filler** (ADR-005) — maps `lines` onto official 1040 fields and must handle every line it needs; (3) the **observation emitter** (ADR-004) — surfaces computed values; (4) the **test suite** — asserts each field against hand-computed expectations. Adding a tax line means extending `TaxResult.lines` and the PDF field map together.
