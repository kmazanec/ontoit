"""Fill and flatten the IRS 2025 Form 1040 with computed tax values.

Entry point: fill_1040(result) -> bytes

Produces a flattened (baked) PDF where form fields are converted to static
text so values render correctly in every viewer, including Adobe Reader.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import fitz  # PyMuPDF

from app.pdf.field_map import CHECKBOX_CHECKED, FIELD_MAP, FILING_STATUS_CHECKBOX
from app.tax.types import TaxResult

# Resolve the PDF asset relative to this module so the path is CWD-independent.
_TEMPLATE = Path(__file__).parent.parent.parent / "assets" / "f1040-2025.pdf"


def _format_dollars(value: Decimal) -> str:
    """Round to whole dollars and format with thousands separator (no sign, no cents).

    IRS instructions direct filers to round cents to the nearest dollar.
    """
    return f"{int(round(value)):,}"


def fill_1040(result: TaxResult) -> bytes:
    """Fill IRS 2025 Form 1040 with values from *result* and return baked PDF bytes.

    The returned PDF is flattened: all AcroForm fields are converted to static
    drawn content so values are visible in every viewer without needing the
    AcroForm render layer.

    PyMuPDF widgets hold a reference to their page via the underlying MuPDF
    annotation. Keeping all page objects alive for the duration of editing is
    required — a Page that is garbage-collected unbinds its annotation, causing
    widget.update() to raise "Annot is not bound to a page".
    """
    doc = fitz.open(str(_TEMPLATE))

    # Keep all pages alive so widget annotations stay bound.
    pages = [doc[i] for i in range(doc.page_count)]

    # Build field_name -> widget index across all pages.
    # Widgets are accessed by re-iterating with pages in scope rather than
    # storing Widget objects directly, because Widget is a thin wrapper around
    # a MuPDF annotation and does not hold its own page reference.
    field_index: dict[str, tuple[int, int]] = {}
    for page_num, page in enumerate(pages):
        for widget_idx, widget in enumerate(page.widgets()):
            field_index[widget.field_name] = (page_num, widget_idx)

    # Decide which fields to fill and their values.
    updates: dict[str, str] = {}
    for line_key, field_name in FIELD_MAP.items():
        if line_key not in result.lines:
            continue
        value = result.lines[line_key]
        # Leave zero fields blank — matches IRS form conventions.
        if value == Decimal("0"):
            continue
        updates[field_name] = _format_dollars(value)

    checkbox_field = FILING_STATUS_CHECKBOX.get(result.filing_status)
    if checkbox_field:
        updates[checkbox_field] = CHECKBOX_CHECKED

    # Apply updates in a single page-by-page pass to keep the page alive
    # throughout each widget.update() call.
    for page_num, page in enumerate(pages):
        for widget in page.widgets():
            new_value = updates.get(widget.field_name)
            if new_value is not None:
                widget.field_value = new_value
                widget.update()

    # Bake (flatten): converts AcroForm fields to static page content so the
    # values render everywhere without the AcroForm layer.
    doc.bake()

    return doc.tobytes()
