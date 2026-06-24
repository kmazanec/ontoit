# ADR-007: Encode the cited, final 2025 tax parameters as versioned data, including the IRS Tax Table

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

Correctness rests entirely on the 2025 tax parameters (ADR-006). The PRD flagged this as its biggest risk (R-1), and research confirmed the risk was real: **the brief's implied $14,600 Single standard deduction is the 2024 figure; the correct 2025 value is $15,750 Single / $31,500 MFJ** (OBBBA, signed July 4 2025; confirmed by the 2025 Form 1040 instructions). Research also established that **incomes under $100,000 must use the IRS Tax Table lookup, not bracket arithmetic** — the most common LLM/implementer error (TaxCalcBench). And it computed the sample filer's exact return: taxable income $28,879.35, tax **$3,227**, refund **$4,405**, both credits **$0**.

## Options considered

- **Hardcode parameters inline in the engine.** Fast, but un-citable, untestable in isolation, and easy to get wrong (as the brief did). Rejected.
- **Compute tax from bracket percentages.** Simpler than a table, but **wrong** for sub-$100k incomes — the IRS requires the Tax Table (rounds taxable income to the nearest $50, returns a pre-computed amount); bracket math gives a different number. Rejected for the table-required range.
- **Versioned, cited parameter data + the IRS Tax Table, injected into the pure engine (chosen).** Each figure carries its IRS source; the engine reads them; tests assert against hand-computed expectations.

## Decision

Encode the **final 2025** parameters as a versioned data module the pure tax engine consumes: standard deduction ($15,750 Single / $31,500 MFJ); the **IRS 2025 Tax Table** as `(income_floor, income_ceiling, tax)` rows for the table-required range (binary-searched), with the bracket schedule retained only for incomes ≥ $100k (out of target but kept correct); 2025 Saver's Credit AGI tiers (Single 50%≤$23,750 / 20%≤$25,500 / 10%≤$39,500 / 0% above; MFJ tiers double); 2025 EITC parameters (max credit and income/AGI limits by qualifying-children count, $11,950 investment-income limit, age 25–64 childless rule). Every value carries an inline citation to its IRS primary source.

## Rationale

This directly retires the PRD's top risk: the figures are the *correct 2025* ones, each defensible by citation, and the Tax-Table-over-brackets rule is honored so the sample filer's tax is exactly $3,227 — matching three independent calculators. Injecting the parameters keeps the engine pure and lets a test assert the sample return to the cent (AC6). The data is versioned so a future tax year is a data change, not a logic change.

## Tradeoffs & risks

- **Gave up:** the simplicity of inline constants — we maintain a parameter module and a Tax Table excerpt. Worth it: it is the difference between a right and wrong refund.
- **Risk (carried from research, verify before hardcoding):** the $15,750/$31,500 figures derive from OBBBA; confirm against the published 2025 Form 1040 instructions before the build freezes them. Box 12-W → Form 8889 Line 9 routing is medium-confidence — verify against 2025 Form 8889 instructions if HSA is ever surfaced (it is not, per ADR's HSA non-action / PRD R10).
- **Risk:** transcription error in the Tax Table excerpt. *Mitigation:* test the sample row and the bracket-boundary rows against IRS values.
- **Revisit:** annually, or if Congress amends 2025 figures.

## Consequences for the build

- **Policy:** sub-$100k tax is computed by **Tax Table lookup**, never bracket math. Money is `Decimal`. Each parameter cites its IRS source in-code.
- **Policy:** the sample filer's expected return ($28,879.35 taxable / $3,227 tax / $4,405 refund / $0 credits) is a golden test fixture (AC6, AC8, AC9, AC11).
- **Contract consequences (Contract: yes — the tax-parameter data shape):**
  - **Source of truth:** `app/tax/params_2025.py` (parameters + Tax Table) — the single place 2025 figures live.
  - **Shape (minimum viable):** `STANDARD_DEDUCTION: dict[FilingStatus, Decimal]`; `TAX_TABLE: list[tuple[Decimal, Decimal, Decimal]]` (floor, ceiling, tax) for the table range + `BRACKETS: dict[FilingStatus, list[Bracket]]` for ≥$100k; `SAVERS_TIERS: dict[FilingStatus, list[tuple[Decimal, Decimal]]]` (agi_ceiling, rate); `EITC: dict[int, EitcParams]` keyed by qualifying-children count with per-status limits.
  - **Exhaustive consumers:** the tax engine (`compute_tax`) reads all of these; the parameter test asserts each against its IRS citation. Adding a filing status means adding its entry to every status-keyed dict — a missing key is a build defect.
