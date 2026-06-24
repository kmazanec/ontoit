"""Tests for the W-2 extraction module.

Covers:
  - pdfplumber text-layer extraction of the bundled sample PDF
  - input validation rejection cases
  - W2 <-> cookie dict round-trip
  - Vision routing (monkeypatched; no live API calls in tests)
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.extraction import (
    ExtractionResult,
    extract_w2,
    w2_from_dict,
    w2_to_dict,
    _extract_vision,
    _parse_vision_response,
    _validate,
)
from app.tax.types import Box12Entry, W2

SAMPLE_PDF = Path(__file__).resolve().parent.parent / "assets" / "sample-w2.pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sample() -> bytes:
    return SAMPLE_PDF.read_bytes()


# ---------------------------------------------------------------------------
# pdfplumber text-layer extraction of the sample PDF
# ---------------------------------------------------------------------------


def test_pdfplumber_extracts_sample_wages_and_withholding():
    result = extract_w2(_load_sample(), "application/pdf")
    assert result.ok, f"Extraction failed: {result.errors}"
    assert result.source == "text"
    assert result.w2 is not None
    assert result.w2.wages == Decimal("44629.35")
    assert result.w2.federal_withholding == Decimal("7631.62")


def test_pdfplumber_extracts_sample_box12_entries():
    result = extract_w2(_load_sample(), "application/pdf")
    assert result.ok, f"Extraction failed: {result.errors}"
    assert result.w2 is not None
    box12 = {e.code: e.amount for e in result.w2.box12}
    # The sample PDF uses code E for the 401(k) deferral and W for the HSA.
    assert Decimal("4107.00") in box12.values()
    assert Decimal("1500.00") in box12.values()
    # Both entries must be present.
    assert len(result.w2.box12) >= 2


def test_pdfplumber_result_uses_decimal_not_float():
    result = extract_w2(_load_sample(), "application/pdf")
    assert result.ok
    assert isinstance(result.w2.wages, Decimal)
    assert isinstance(result.w2.federal_withholding, Decimal)
    for entry in result.w2.box12:
        assert isinstance(entry.amount, Decimal)


# ---------------------------------------------------------------------------
# Validation rejection cases
# ---------------------------------------------------------------------------


def test_validation_rejects_negative_wages():
    errors = _validate(Decimal("-1.00"), Decimal("500.00"), [])
    assert any("wages" in e.lower() or "positive" in e.lower() for e in errors)


def test_validation_rejects_box2_gte_box1():
    # Federal withholding equal to wages is illegal.
    errors = _validate(Decimal("1000.00"), Decimal("1000.00"), [])
    assert any("less than" in e.lower() or ">=" in e or "must be" in e for e in errors)

    # Withholding exceeding wages is also illegal.
    errors = _validate(Decimal("1000.00"), Decimal("1200.00"), [])
    assert any("less than" in e.lower() or ">=" in e or "must be" in e for e in errors)


def test_validation_rejects_malformed_box12_code():
    # A code that is not purely alphabetic (OCR collapse to digits) must fail.
    errors = _validate(
        Decimal("50000.00"),
        Decimal("8000.00"),
        [{"code": "D1", "amount": Decimal("4000.00")}],
    )
    assert any("code" in e.lower() for e in errors)

    # An empty code also fails.
    errors = _validate(
        Decimal("50000.00"),
        Decimal("8000.00"),
        [{"code": "", "amount": Decimal("4000.00")}],
    )
    assert any("code" in e.lower() for e in errors)


def test_validation_returns_empty_list_for_valid_inputs():
    errors = _validate(
        Decimal("44629.35"),
        Decimal("7631.62"),
        [
            {"code": "E", "amount": Decimal("4107.00")},
            {"code": "W", "amount": Decimal("1500.00")},
        ],
    )
    assert errors == []


# ---------------------------------------------------------------------------
# W2 <-> cookie dict round-trip
# ---------------------------------------------------------------------------


def test_w2_to_dict_produces_string_amounts():
    w2 = W2(
        wages=Decimal("44629.35"),
        federal_withholding=Decimal("7631.62"),
        box12=(
            Box12Entry(code="E", amount=Decimal("4107.00")),
            Box12Entry(code="W", amount=Decimal("1500.00")),
        ),
    )
    d = w2_to_dict(w2)
    assert d["wages"] == "44629.35"
    assert d["federal_withholding"] == "7631.62"
    assert isinstance(d["wages"], str)
    assert isinstance(d["box12"][0]["amount"], str)


def test_w2_round_trip_preserves_values():
    original = W2(
        wages=Decimal("44629.35"),
        federal_withholding=Decimal("7631.62"),
        box12=(
            Box12Entry(code="E", amount=Decimal("4107.00")),
            Box12Entry(code="W", amount=Decimal("1500.00")),
        ),
    )
    restored = w2_from_dict(w2_to_dict(original))
    assert restored.wages == original.wages
    assert restored.federal_withholding == original.federal_withholding
    assert restored.box12 == original.box12


def test_w2_round_trip_uses_decimal():
    original = W2(wages=Decimal("99999.99"), federal_withholding=Decimal("12345.67"))
    restored = w2_from_dict(w2_to_dict(original))
    assert isinstance(restored.wages, Decimal)
    assert isinstance(restored.federal_withholding, Decimal)


# ---------------------------------------------------------------------------
# Vision routing (monkeypatched — no live API calls)
# ---------------------------------------------------------------------------


def test_image_input_routes_to_vision(monkeypatch):
    """A JPEG upload must not attempt pdfplumber; it must call _extract_vision."""
    vision_called = []

    def fake_vision(file_bytes: bytes, content_type: str) -> ExtractionResult:
        vision_called.append(content_type)
        return ExtractionResult(
            ok=True,
            w2=W2(
                wages=Decimal("50000.00"),
                federal_withholding=Decimal("8000.00"),
            ),
            source="vision",
        )

    monkeypatch.setattr("app.extraction._extract_vision", fake_vision)

    result = extract_w2(b"fake-jpeg-bytes", "image/jpeg")
    assert vision_called == ["image/jpeg"]
    assert result.source == "vision"
    assert result.ok


def test_pdf_with_no_text_layer_routes_to_vision(monkeypatch):
    """A PDF that yields no text from pdfplumber must fall through to Vision."""
    # Patch _extract_text_layer to simulate a no-text-layer PDF.
    monkeypatch.setattr("app.extraction._extract_text_layer", lambda _bytes: None)

    vision_called = []

    def fake_vision(file_bytes: bytes, content_type: str) -> ExtractionResult:
        vision_called.append(content_type)
        return ExtractionResult(
            ok=True,
            w2=W2(
                wages=Decimal("50000.00"),
                federal_withholding=Decimal("8000.00"),
            ),
            source="vision",
        )

    monkeypatch.setattr("app.extraction._extract_vision", fake_vision)

    result = extract_w2(b"fake-pdf-bytes", "application/pdf")
    assert vision_called == ["application/pdf"]
    assert result.source == "vision"


def test_vision_response_parser_handles_valid_json():
    raw = (
        '{"wages": 44629.35, "federal_withholding": 7631.62, '
        '"box12": [{"code": "E", "amount": 4107.00, "confidence": 0.95},'
        '{"code": "W", "amount": 1500.00, "confidence": 0.90}],'
        '"wages_confidence": 0.98, "withholding_confidence": 0.97}'
    )
    result = _parse_vision_response(raw)
    assert result.ok, f"Unexpected errors: {result.errors}"
    assert result.w2 is not None
    assert result.w2.wages == Decimal("44629.35")
    assert result.w2.federal_withholding == Decimal("7631.62")


def test_vision_response_parser_rejects_low_confidence_wages():
    raw = (
        '{"wages": 44629.35, "federal_withholding": 7631.62, '
        '"box12": [], "wages_confidence": 0.3, "withholding_confidence": 0.97}'
    )
    result = _parse_vision_response(raw)
    assert not result.ok
    assert any("wages" in e.lower() or "confidence" in e.lower() for e in result.errors)
