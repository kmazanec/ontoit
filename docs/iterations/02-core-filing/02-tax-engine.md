# Feature: Deterministic tax engine (2025 params + IRS Tax Table)

**ID:** F-03 · **Iteration:** 02-core-filing · **Status:** Not started

## What this delivers (before → after)
**Before:** No tax math exists.
**After:** A pure, deterministic `compute_tax(w2, answers) → TaxResult` returns a correct 2025 Form 1040 computation — for the sample Single filer, taxable income $28,879.35, tax $3,227 (from the IRS 2025 Tax Table), refund $4,405, both credits $0 — plus a line-by-line trace, all unit-proven by a golden test.

## How it fits the roadmap
The correctness core and the PRD's highest risk, de-risked early as a standalone, headless, unit-tested feature. It has **no hard dependency on F-02** — it consumes the frozen `W2`/`TaxResult` contracts, not F-02's runtime — so it builds concurrently with F-02. F-04 and F-05 consume its shipped behavior.

## Requirements traced (from the PRD)
R6 (core computation), R7 (Saver's Credit), R8 (EITC), R9 (filing-status correctness), R10 (HSA non-action). Acceptance: AC6 (Single core path, exact values), AC7 (MFJ differs), AC8 (Saver's across cases), AC9 (EITC across cases), AC11 (HSA not double-counted).

## Dependencies (must exist before this starts)
- **None — can start as soon as the iteration's contracts are frozen.** (It introduces the `TaxResult`/`W2`/`Answers` types and the 2025-parameter data; it does not consume any feature's runtime behavior.)
- External: confirm the OBBBA-derived 2025 figures against the published IRS 2025 Form 1040 instructions before hardcoding (a verification task, not a dependency).

## Unblocks (what waits on this)
- F-04 (conversation) — calls `compute_tax` to show results.
- F-05 (PDF) — fills the official form from a `TaxResult`.
- F-07 (correction) and F-08 (trace panel) — recompute / render the trace.

## Contracts touched
- **TaxResult / W2 / Answers** (source of truth: ADR-006) — INTRODUCES these types (`app/tax/types.py`), incl. `TaxResult.lines` for the PDF filler. Money is `Decimal`. F-02 extends `W2`; F-04 extends `Answers`.
- **2025 tax parameters + IRS Tax Table** (source of truth: ADR-007) — INTRODUCES `app/tax/params_2025.py`: standard deduction ($15,750 Single / $31,500 MFJ), the IRS 2025 Tax Table (binary-searched) for sub-$100k incomes, Saver's tiers, EITC params; each value cites its IRS source.
- **ObservationEvent** (source of truth: ADR-004) — emits computed-value/decision events (incl. credit-eligibility reasons).

## Acceptance criteria (product behavior)
1. Given the sample W-2 + Single + 0 dependents, `compute_tax` returns taxable income 28879.35, tax 3227 (via Tax Table lookup, **not** bracket arithmetic), total payments 7631.62, refund 4405 (AC6); Saver's Credit 0 with reason "AGI 44629 > $39,500 cutoff" (AC8); EITC 0 with reason "0 children, AGI > $19,104" (AC9).
2. Given the same W-2 + MFJ, the standard deduction ($31,500), brackets, and credit thresholds used are the MFJ 2025 values and refund/owed differs accordingly (AC7).
3. Given a qualifying filer (e.g. MFJ at this AGI with 1 qualifying child), EITC returns the correct non-zero 2025 amount (AC9).
4. Given the sample's Box 12-W = 1500.00, it is not added to income and produces no extra 1040 line (AC11, R10).
5. `compute_tax` is pure (no I/O, no clock, no network) and deterministic — identical inputs yield identical outputs.
6. The function returns a line-by-line trace `(label, value, explanation)` consistent with the computed values (feeds F-08).

## Testing requirements
- Unit (golden): the sample Single return asserted to the cent; MFJ variant; Saver's at a qualifying AGI (non-zero) and the sample (zero); EITC for MFJ+1-child (non-zero) and the sample (zero); HSA non-action.
- Unit: the 2025 parameters asserted against their IRS-cited values; the Tax Table sample row and bracket-boundary rows.
- Property: determinism (repeat-run equality).

## Manual setup required
- Confirm the 2025 standard-deduction / bracket / Saver's / EITC figures against published IRS 2025 Form 1040 instructions before freezing (research currently high-confidence from primary sources; OBBBA-derived).

## Implementation notes (filled in by the building agent)
