# Feature: Filled official IRS 2025 Form 1040 PDF (PyMuPDF + bake)

**ID:** F-05 · **Iteration:** 02-core-filing · **Status:** Not started

## What this delivers (before → after)
**Before:** The computed return exists only as on-screen values.
**After:** The user downloads a completed **official IRS 2025 Form 1040** PDF, populated with the computed line values and flattened (baked) so it renders correctly in any viewer including Adobe Reader.

## How it fits the roadmap
Completes the end-to-end local filing flow for iteration 02 (download is the user's final artifact). Hard-depends on F-03 (fills from a real `TaxResult`); independent of F-04.

## Requirements traced (from the PRD)
R11 (filled official form), R12 (the fill is a real tool action). Acceptance: AC12 (downloadable filled official 1040 with the computed line values).

## Dependencies (must exist before this starts)
- **F-03 (tax engine)** — HARD dep: consumes a real `TaxResult` (its `lines`) to populate the form.
- External: download the official IRS 2025 `f1040.pdf` and run the field-enumeration spike against it (a setup step inside this feature).

## Unblocks (what waits on this)
- F-06 (deploy) — the working filer (incl. download) must exist to deploy.

## Contracts touched
- **1040 field map** (source of truth: ADR-005) — INTRODUCES `app/pdf/field_map.py` (logical line → discovered AcroForm field name), populated from the enumeration spike.
- **TaxResult** (source of truth: ADR-006) — consumes `TaxResult.lines`; every 1040 line produced must have a `FIELD_MAP` entry.
- **ObservationEvent** (source of truth: ADR-004) — emits a "filled/ready to download" event.

## Acceptance criteria (product behavior)
1. Given a completed conversation/computation, when the user requests the form, then a downloadable file is returned that is the official IRS 2025 Form 1040 populated with the computed values: line 1a wages, withholding, standard deduction, taxable income, tax, any credits, and refund/amount owed (AC12).
2. The downloaded PDF renders the filled values correctly when opened in a standard viewer **and** Adobe Reader (achieved via `bake()` to flat static text, not relying on NeedAppearances).
3. The filing-status checkbox (Single vs. MFJ) is correctly set on the form (handling the IRS non-standard `Yes`/`Off` state names).
4. For the sample Single filer, the baked PDF shows tax 3227 and refund 4405 on the correct lines.

## Testing requirements
- Unit: the field-map covers every 1040 line `TaxResult.lines` produces (no missing mapping); checkbox state set correctly.
- Integration: fill + bake the official form from the sample `TaxResult`; assert key line values are present as static text in the output and the filing-status box is checked.
- Render: confirm (at least once, documented) the baked output opens correctly in Adobe Reader.

## Manual setup required
- Download the official IRS 2025 `f1040.pdf` and run the field-enumeration script against it to discover current AcroForm field names (names are not published and may change in the 2025 revision; the form embeds an XFA stream).

## Implementation notes (filled in by the building agent)
