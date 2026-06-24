# ADR-005: Fill the official IRS 2025 1040 with PyMuPDF, then bake() to flat static text

**Status:** Accepted · **Date:** 2026-06-24 · **Stretch:** no · **Contract:** yes
**Supersedes:** none · **Superseded by:** none

## Context

The deliverable is a downloadable file that is the **official IRS 2025 Form 1040** populated with computed values (R11, AC12), and it must render correctly when a judge opens or prints it — including in Adobe Reader, which the IRS recommends. The IRS does not publish a field-name schema for the 1040 AcroForm; names (`f1_01[0]`, …) are discovered by inspecting `https://www.irs.gov/pub/irs-pdf/f1040.pdf`.

## Options considered

- **pypdf `update_page_form_field_values()`.** Documented to not regenerate appearance streams — filled values display **blank** until the field is clicked/re-saved, and silently blanks non-Latin/subset-font glyphs. Unusable for a download-and-print demo (TECHNOLOGY.md, High confidence). Rejected.
- **pdfrw + `NeedAppearances`.** Pure-Python, simple, but GitHub issue #213 documents filled PDFs failing to open in Adobe Reader on Windows for some users — risky given the IRS's Adobe recommendation (medium-confidence scope). Keeps fields interactive.
- **PyMuPDF (`fitz`) fill + `bake()` (chosen).** Fills AcroForm widgets via `widget.update()`, then `bake()` flattens fields to static searchable text — eliminating NeedAppearances rendering inconsistencies and Adobe-version dependencies entirely.

## Decision

Use **PyMuPDF** to fill the official IRS 2025 Form 1040 AcroForm fields, then **`bake()`** the result to flat static text for the downloadable file. Field names are discovered by a one-time enumeration script run against the live `f1040.pdf`, captured in a checked-in field-map module.

## Rationale

`bake()` produces a file that renders correctly in every viewer including Adobe Reader, with no NeedAppearances gamble and no interactive-field fragility — the most robust path to "the judge opens the PDF and sees a correctly filled 1040." Flattening also means the output cannot be accidentally edited, which suits a "review-and-sign" self-prepared artifact (DOMAIN.md §8, the tool-not-preparer posture).

## Tradeoffs & risks

- **Gave up:** an interactive (still-fillable) output PDF; baked fields are static. Acceptable — the deliverable is a *completed* return, not a template.
- **Risk:** IRS checkboxes use non-standard `'Yes'`/`'Off'` state names that some engines silently revert (PyMuPDF issue #4055). *Mitigation:* handle checkbox state names explicitly (filing-status checkbox) and assert in a test that the rendered box is checked.
- **Risk:** IRS field names may change in the 2025 revision and the form embeds an XFA stream. *Mitigation:* the enumeration script is re-run against the live form before building the field map; the map is a single source-of-truth module.
- **Revisit if:** `bake()` proves lossy for any needed field, fall back to read-only flags.

## Consequences for the build

- **Policy:** the downloadable 1040 is always flattened (baked) before download; a test asserts key line values are present as static text and the filing-status checkbox is set.
- **Policy:** run the field-enumeration script against the live `f1040.pdf` first; never hardcode field names without verifying against the current form.
- **Contract consequences (Contract: yes — the 1040 field map):**
  - **Source of truth:** `app/pdf/field_map.py` — maps logical 1040 lines → AcroForm field names.
  - **Shape (minimum viable):** `FIELD_MAP: dict[str, str]` keyed by logical line id (`"line_1a_wages"`, `"line_12_std_deduction"`, `"line_15_taxable_income"`, `"line_16_tax"`, `"line_19_child_credit"`/credits, `"line_25a_withholding"`, `"line_34_refund"`, `"line_37_owed"`, `"filing_status_single"`, `"filing_status_mfj"`) → the discovered AcroForm name.
  - **Exhaustive consumers:** the PDF filler (writes every mapped line from `TaxResult.lines`, ADR-006) and its test (asserts each appears baked). Every line the tax engine produces that belongs on the 1040 must have a `FIELD_MAP` entry — a missing mapping is a build defect.
