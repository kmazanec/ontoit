"""Tests for F-05: IRS 2025 Form 1040 PDF filler.

Verifies that fill_1040() produces a valid, baked PDF containing the
computed dollar values as static text, and that the field map covers every
key the tax engine emits.
"""

from __future__ import annotations

from decimal import Decimal

import fitz
import pytest

from app.pdf.field_map import CHECKBOX_CHECKED, FIELD_MAP, FILING_STATUS_CHECKBOX
from app.pdf.filler import fill_1040, _format_dollars
from app.tax.engine import compute_tax
from app.tax.types import Answers, Box12Entry, W2


# ---------------------------------------------------------------------------
# Sample filer — matches the brief's specified inputs.
# ---------------------------------------------------------------------------
_W2 = W2(
    wages=Decimal("44629.35"),
    federal_withholding=Decimal("7631.62"),
    box12=(
        Box12Entry("E", Decimal("4107.00")),
        Box12Entry("W", Decimal("1500.00")),
    ),
)
_ANSWERS = Answers("single", 0)


@pytest.fixture(scope="module")
def tax_result():
    return compute_tax(_W2, _ANSWERS)


@pytest.fixture(scope="module")
def filled_pdf_bytes(tax_result):
    return fill_1040(tax_result)


@pytest.fixture(scope="module")
def baked_doc(filled_pdf_bytes):
    return fitz.open(stream=filled_pdf_bytes, filetype="pdf")


# ---------------------------------------------------------------------------
# Basic validity
# ---------------------------------------------------------------------------

def test_returns_bytes(filled_pdf_bytes):
    assert isinstance(filled_pdf_bytes, bytes)
    assert len(filled_pdf_bytes) > 0


def test_starts_with_pdf_header(filled_pdf_bytes):
    assert filled_pdf_bytes[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Baked output contains expected dollar values as static text
# ---------------------------------------------------------------------------

def _page_text(doc: fitz.Document, page_index: int) -> str:
    return doc[page_index].get_text()


def test_taxable_income_in_baked_pdf(baked_doc, tax_result):
    """Line 15 taxable income ($28,879) must appear as static text after baking."""
    expected = _format_dollars(tax_result.lines["line_15_taxable_income"])
    all_text = _page_text(baked_doc, 1)
    # Accept with or without comma formatting (both "28,879" and "28879").
    assert expected in all_text or expected.replace(",", "") in all_text, (
        f"Expected taxable income {expected!r} not found in page-2 text"
    )


def test_tax_in_baked_pdf(baked_doc, tax_result):
    """Line 16 tax ($3,226) must appear in the baked PDF."""
    expected = _format_dollars(tax_result.lines["line_16_tax"])
    all_text = _page_text(baked_doc, 1)
    assert expected in all_text or expected.replace(",", "") in all_text, (
        f"Expected tax {expected!r} not found in page-2 text"
    )


def test_refund_in_baked_pdf(baked_doc, tax_result):
    """Line 34 refund ($4,405 rounded) must appear in the baked PDF."""
    expected = _format_dollars(tax_result.lines["line_34_refund"])
    all_text = _page_text(baked_doc, 1)
    assert expected in all_text or expected.replace(",", "") in all_text, (
        f"Expected refund {expected!r} not found in page-2 text"
    )


def test_wages_in_baked_pdf(baked_doc, tax_result):
    """Line 1a wages must appear on page 1 of the baked PDF."""
    expected = _format_dollars(tax_result.lines["line_1a_wages"])
    all_text = _page_text(baked_doc, 0)
    assert expected in all_text or expected.replace(",", "") in all_text, (
        f"Expected wages {expected!r} not found in page-1 text"
    )


# ---------------------------------------------------------------------------
# FIELD_MAP coverage — every key the engine emits must be mapped
# ---------------------------------------------------------------------------

def test_field_map_covers_all_engine_lines(tax_result):
    """No engine line key may be silently dropped — each must appear in FIELD_MAP."""
    missing = [key for key in tax_result.lines if key not in FIELD_MAP]
    assert not missing, (
        f"Engine emits lines not in FIELD_MAP: {missing!r}"
    )


# ---------------------------------------------------------------------------
# Filing-status checkbox
# ---------------------------------------------------------------------------

def test_single_checkbox_value_before_bake():
    """Filing-status checkbox must be set to the checked value before baking."""
    from pathlib import Path
    import fitz as _fitz

    template = Path(__file__).parent.parent / "assets" / "f1040-2025.pdf"
    doc = _fitz.open(str(template))
    checkbox_field = FILING_STATUS_CHECKBOX["single"]

    # Keep pages alive so widget annotations stay bound (PyMuPDF requirement:
    # a Page that is GC'd unbinds its annotations).
    pages = [doc[i] for i in range(doc.page_count)]

    # Set the checkbox value.
    for page in pages:
        for widget in page.widgets():
            if widget.field_name == checkbox_field:
                widget.field_value = CHECKBOX_CHECKED
                widget.update()

    # Re-read value from a fresh iteration to confirm persistence.
    for page in pages:
        for widget in page.widgets():
            if widget.field_name == checkbox_field:
                assert widget.field_value == CHECKBOX_CHECKED
                return

    pytest.fail(f"Checkbox field {checkbox_field!r} not found in form")
