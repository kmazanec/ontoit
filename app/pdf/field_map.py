"""AcroForm field mapping for IRS 2025 Form 1040 (f1040-2025.pdf).

Field names follow the XFA/AcroForm naming convention in the PDF:
  - Page 1 fields: topmostSubform[0].Page1[0].f1_NN[0]
  - Page 2 fields: topmostSubform[0].Page2[0].f2_NN[0]

The right-column money fields were identified by cross-referencing each
widget's y-coordinate with the nearest label text extracted from the same
page, then confirming against the published 2025 Form 1040 line order.

Filing-status checkboxes: the IRS uses the non-standard checked-state value
'1' instead of the PDF spec's conventional 'Yes'. This quirk is confirmed in
the states manifest (f1040_fields.json) where every checkbox shows
{'normal': ['1'], 'down': ['1', 'Off']}.
"""

# Maps each logical TaxResult.lines key to the corresponding AcroForm field name.
# Every key present in TaxResult.lines must appear here.
FIELD_MAP: dict[str, str] = {
    # Page 1 — income section
    "line_1a_wages": "topmostSubform[0].Page1[0].f1_47[0]",
    # Page 2 — Tax and Credits
    "line_11_agi": "topmostSubform[0].Page2[0].f2_01[0]",
    "line_12_std_deduction": "topmostSubform[0].Page2[0].f2_02[0]",
    "line_15_taxable_income": "topmostSubform[0].Page2[0].f2_06[0]",
    "line_16_tax": "topmostSubform[0].Page2[0].f2_08[0]",
    # Saver's Credit + EITC flow through Schedule 3 → line 20 (f2_12)
    "line_19_credits": "topmostSubform[0].Page2[0].f2_12[0]",
    # Line 24 is the 2025 form's "total tax" (line 22 minus credits + line 23 other taxes)
    "line_22_total_tax": "topmostSubform[0].Page2[0].f2_16[0]",
    # Page 2 — Payments
    "line_25a_withholding": "topmostSubform[0].Page2[0].f2_17[0]",
    "line_33_total_payments": "topmostSubform[0].Page2[0].f2_29[0]",
    # Page 2 — Refund / Amount Owed
    "line_34_refund": "topmostSubform[0].Page2[0].f2_30[0]",
    "line_37_owed": "topmostSubform[0].Page2[0].f2_35[0]",
}

# Maps filing status values to the full AcroForm checkbox field name.
# Checked state is '1' (IRS non-standard; see module docstring).
FILING_STATUS_CHECKBOX: dict[str, str] = {
    "single": "topmostSubform[0].Page1[0].c1_1[0]",
    "mfj": "topmostSubform[0].Page1[0].c1_2[0]",
}

# The value that checks a filing-status checkbox in this form.
CHECKBOX_CHECKED: str = "1"
