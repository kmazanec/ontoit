# Feature: "Show your work" tax-trace panel (stretch)

**ID:** F-08 · **Iteration:** 03-deploy-and-stretch · **Status:** Not started

## What this delivers (before → after)
**Before:** The user sees only the final refund number.
**After:** The user sees the 1040 computed line-by-line with reasoning — "Taxable income = $44,629 − $15,750 standard deduction = $28,879"; "Tax = $3,227 (IRS 2025 Tax Table, $28,850–$28,900 row)"; "Saver's Credit = $0 (AGI $44,629 exceeds the $39,500 Single cutoff)" — making correctness inspectable rather than asserted.

## How it fits the roadmap
Committed stretch feature; turns the deterministic engine into a visible demo asset for a harness-focused judge. Hard-depends on F-03 (renders its trace) and F-01 (the panel surface).

## Requirements traced (from the PRD)
PRD §4 Committed stretch 2; R17 (the trace doubles as the agent's plain-language explanation). Acceptance: AC20 (tax-trace panel).

## Dependencies (must exist before this starts)
- **F-03 (tax engine)** — HARD dep: consumes the line-by-line trace `(label, value, explanation)` the engine produces.
- **F-01 (walking skeleton)** — HARD dep: consumes the UI/observation surface to render the panel.

## Unblocks (what waits on this)
- None.

## Contracts touched
- **ObservationEvent** (source of truth: ADR-004) — trace steps emit as events feeding both the panel and the agent's explanation.
- **TaxResult** (source of truth: ADR-006) — consumes the trace produced alongside the result (single source of truth; trace cannot diverge from the values).

## Acceptance criteria (product behavior)
1. Given a computed return, the panel presents the 1040 line-by-line with reasoning for each load-bearing line: taxable income, the Tax Table lookup, tax, each credit with its eligibility reason, and refund/owed (AC20).
2. Each value shown in the trace matches the corresponding value on the filled 1040 (no divergence) (AC20).
3. For the sample filer, the trace shows the $0 credits **with their reasons** ($39,500 Saver's cutoff; $19,104 childless EITC limit) — the legibility moment.

## Testing requirements
- Unit: the trace strings and values match the golden sample fixture; trace values equal the corresponding `TaxResult` fields.
- Integration: completing a sample session renders a trace panel whose lines match the downloaded 1040.

## Manual setup required
None.

## Implementation notes (filled in by the building agent)
