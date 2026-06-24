"""W-2 extraction: pdfplumber text-layer parsing with a Claude Vision fallback.

Two-step strategy:
  1. pdfplumber — deterministic for digital PDFs with a text layer. Uses both a
     text regex pass and coordinate cropping to pull Box 1 wages, Box 2 federal
     withholding, and Box 12 code/amount pairs from the fixed IRS W-2 layout.
  2. Claude Vision — fallback for scanned / image-only inputs, or when pdfplumber
     cannot locate the required fields. Returns a strict JSON payload with per-field
     confidence so low-confidence values can be flagged before going to the engine.

Validation guards run before returning; money is always Decimal, never float.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import anthropic
import pdfplumber

from app.tax.types import Box12Entry, W2

# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult:
    ok: bool
    w2: W2 | None
    source: str  # "text" | "vision" | "sample"
    errors: list[str] = field(default_factory=list)
    confidence: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cookie serialisation helpers
# ---------------------------------------------------------------------------


def w2_to_dict(w2: W2) -> dict[str, Any]:
    """Flatten a W2 into a cookie-safe dict (Decimal → str, tuples → lists).

    Decimal is not JSON-serialisable; storing amounts as strings preserves
    exact precision across the round-trip without floating-point drift.
    """
    return {
        "wages": str(w2.wages),
        "federal_withholding": str(w2.federal_withholding),
        "box12": [{"code": e.code, "amount": str(e.amount)} for e in w2.box12],
    }


def w2_from_dict(data: dict[str, Any]) -> W2:
    """Reconstruct a W2 from a cookie dict produced by ``w2_to_dict``."""
    box12 = tuple(
        Box12Entry(code=e["code"], amount=Decimal(str(e["amount"])))
        for e in data.get("box12", [])
    )
    return W2(
        wages=Decimal(str(data["wages"])),
        federal_withholding=Decimal(str(data["federal_withholding"])),
        box12=box12,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# IRS plausibility window for Box 2 / Box 1; outside this range we warn but
# do not hard-fail (legitimate withholding can be outside it for edge cases).
_WITHHOLDING_LOW = Decimal("0.10")
_WITHHOLDING_HIGH = Decimal("0.37")

# Guard: code must be 1–2 uppercase letters; amount must be a valid decimal.
_BOX12_CODE_RE = re.compile(r"^[A-Z]{1,2}$")


def _validate(
    wages: Decimal,
    federal_withholding: Decimal,
    box12: list[dict[str, Any]],
) -> list[str]:
    """Return a list of error strings (empty → valid)."""
    errors: list[str] = []

    if wages <= 0:
        errors.append(f"Box 1 wages must be positive, got {wages}")

    if federal_withholding < 0:
        errors.append(
            f"Box 2 federal withholding must be non-negative, got {federal_withholding}"
        )

    # Hard-fail: withholding can never equal or exceed wages.
    if federal_withholding >= wages:
        errors.append(
            f"Box 2 ({federal_withholding}) must be less than Box 1 wages ({wages})"
        )

    # Plausibility flag only (not a hard failure).
    if wages > 0 and not errors:
        ratio = federal_withholding / wages
        if not (_WITHHOLDING_LOW <= ratio <= _WITHHOLDING_HIGH):
            errors.append(
                f"Box 2 / Box 1 ratio {ratio:.1%} is outside the expected 10–37% range"
            )

    for entry in box12:
        code = entry.get("code", "")
        amount = entry.get("amount")
        if not _BOX12_CODE_RE.match(str(code)):
            errors.append(f"Box 12 code {code!r} is not a valid 1–2-letter code")
        try:
            Decimal(str(amount))
        except InvalidOperation:
            errors.append(f"Box 12 amount {amount!r} for code {code!r} is not a number")

    return errors


# ---------------------------------------------------------------------------
# pdfplumber text-layer extraction
# ---------------------------------------------------------------------------


def _decimal(raw: str) -> Decimal:
    """Strip commas and convert to Decimal. Raises InvalidOperation on failure."""
    return Decimal(raw.replace(",", ""))


def _extract_text_layer(pdf_bytes: bytes) -> ExtractionResult | None:
    """Parse Box 1, Box 2, and Box 12 from a digital W-2 PDF text layer.

    Returns None if the text layer is absent or the required fields cannot be
    found, signalling the caller to fall back to Vision.

    The IRS W-2 is a fixed-layout form. The employee reference copy (first
    block on the page) puts Box 1 wages and Box 2 withholding on the line
    immediately after the label ``1 Wages,tips,othercomp. 2 Federal…``.  Box
    12 entries each consist of a 1–2-letter code followed by the dollar amount
    on or near the ``12a`` label row.
    """
    try:
        import io

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                return None
            page = pdf.pages[0]
            text = page.extract_text() or ""
            if not text.strip():
                return None  # image-only / no text layer

            wages, withholding = _parse_box1_box2(text)
            if wages is None or withholding is None:
                return None

            box12_raw = _parse_box12_text(text)
            if not box12_raw:
                # Fall through to coordinate pass before giving up.
                box12_raw = _parse_box12_coords(page)

    except Exception:
        return None

    errors = _validate(wages, withholding, box12_raw)
    if errors:
        return ExtractionResult(ok=False, w2=None, source="text", errors=errors)

    w2 = W2(
        wages=wages,
        federal_withholding=withholding,
        box12=tuple(
            Box12Entry(code=e["code"], amount=Decimal(str(e["amount"])))
            for e in box12_raw
        ),
    )
    return ExtractionResult(
        ok=True,
        w2=w2,
        source="text",
        confidence={"wages": 1.0, "federal_withholding": 1.0, "box12": 1.0},
    )


def _parse_box1_box2(text: str) -> tuple[Decimal | None, Decimal | None]:
    """Find Box 1 wages and Box 2 federal withholding via a two-line pattern.

    The IRS W-2 layout puts the label on one line and the two values on the
    next line separated by whitespace.
    """
    lines = text.split("\n")
    # Pattern: label line containing '1' and 'Wages' and '2' and 'Federal'
    label_re = re.compile(r"1\s+Wages.*?2\s+Federal", re.I)
    for i, line in enumerate(lines):
        if label_re.search(line) and i + 1 < len(lines):
            value_line = lines[i + 1]
            # Two decimal numbers separated by whitespace
            nums = re.findall(r"\d[\d,]*\.\d+", value_line)
            if len(nums) >= 2:
                try:
                    return _decimal(nums[0]), _decimal(nums[1])
                except InvalidOperation:
                    continue
    return None, None


def _parse_box12_text(text: str) -> list[dict[str, Any]]:
    """Extract Box 12 entries from the text layer.

    The employee reference copy typically renders each Box 12 slot as
    ``<CODE> <amount>`` on the line following the Box 12a label.  We scan
    lines after the '12a' marker and collect 1–2-letter uppercase codes
    paired with the following decimal amount.
    """
    lines = text.split("\n")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Find lines that are in the Box 12 neighbourhood (after '12a' label).
    in_box12 = False
    for line in lines:
        if re.search(r"12a\s*See", line, re.I):
            in_box12 = True
            continue
        if in_box12:
            # The IRS layout places Box 12 slots 12a–12d in a column that
            # visually overlaps with Box 14 in some ADP-generated W-2s: the
            # 12b/12c/12d codes appear on the same text line as "14 Other".
            # Do NOT stop at "14 Other" — scan those lines for code+amount
            # pairs as well.  Stop only at the Box 13 checkbox row or at the
            # next copy's repeated "1 Wages" label.
            if re.match(r"13\s*State|1\s+Wages", line):
                break
            # Pull all CODE amount pairs from this line.
            for match in re.finditer(r"\b([A-Z]{1,2})\s+([\d,]+\.\d+)", line):
                code, raw_amount = match.group(1), match.group(2)
                if code in seen:
                    continue
                seen.add(code)
                try:
                    entries.append({"code": code, "amount": _decimal(raw_amount)})
                except InvalidOperation:
                    pass

    return entries


def _parse_box12_coords(page: Any) -> list[dict[str, Any]]:
    """Coordinate-based Box 12 extraction for the first W-2 copy on the page.

    The employee reference copy occupies roughly the top-left quadrant.
    We crop to the region where the IRS layout places Box 12 slots and look
    for single-letter / two-letter codes immediately left of dollar amounts.
    """
    # These bounding-box values are calibrated to the University of Pittsburgh
    # (ADP-generated) W-2 layout.  The box sits at roughly x 100–210, top 295–330.
    try:
        region = page.within_bbox((100, 295, 210, 330))
        words = region.extract_words()
    except Exception:
        return []

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Each code word is followed, on approximately the same horizontal band, by
    # an amount word further to the right.  Sort by vertical position to pair them.
    code_re = re.compile(r"^([A-Z]{1,2})$")
    amount_re = re.compile(r"^\d[\d,]*\.\d+$")

    # Collect (top, text, x0) for codes and amounts separately
    codes: list[tuple[float, str]] = []
    amounts: list[tuple[float, float, str]] = []  # (top, x0, text)
    for w in words:
        t = w["text"]
        # The label "12bW" embeds the code; strip the leading label if present.
        label_strip = re.sub(r"^12[a-d]", "", t)
        if code_re.match(label_strip):
            codes.append((w["top"], label_strip))
        elif amount_re.match(t):
            amounts.append((w["top"], w["x0"], t))

    # Pair each code with the nearest amount within ±6 pt vertically.
    for code_top, code in codes:
        if code in seen:
            continue
        candidates = [
            (abs(amt_top - code_top), amt_text)
            for amt_top, _x0, amt_text in amounts
            if abs(amt_top - code_top) <= 6
        ]
        if candidates:
            _, raw = min(candidates)
            try:
                entries.append({"code": code, "amount": _decimal(raw)})
                seen.add(code)
            except InvalidOperation:
                pass

    return entries


# ---------------------------------------------------------------------------
# Claude Vision fallback
# ---------------------------------------------------------------------------


def _extract_vision(file_bytes: bytes, content_type: str) -> ExtractionResult:
    """Send the document to Claude and ask for a strict JSON extraction.

    Uses the Anthropic document-block API for PDFs and the image-block API for
    JPEG/PNG.  Returns a low-confidence result on parse failure rather than
    raising, so the caller can decide whether to fall back to the sample.
    """
    prompt = (
        "You are reading a US IRS Form W-2. "
        "Return ONLY a valid JSON object — no explanation, no markdown — with exactly these keys:\n"
        '  "wages": number (Box 1),\n'
        '  "federal_withholding": number (Box 2),\n'
        '  "box12": list of {"code": string, "amount": number, "confidence": 0.0-1.0},\n'
        '  "wages_confidence": 0.0-1.0,\n'
        '  "withholding_confidence": 0.0-1.0\n'
        "If a field is not legible, use null for the value and 0.0 for confidence."
    )

    if content_type == "application/pdf":
        b64 = base64.b64encode(file_bytes).decode()
        content: list[dict[str, Any]] = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64,
                },
            },
            {"type": "text", "text": prompt},
        ]
    else:
        b64 = base64.b64encode(file_bytes).decode()
        media = content_type if content_type in ("image/png", "image/jpeg") else "image/png"
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
            {"type": "text", "text": prompt},
        ]

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[{"role": "user", "content": content}],
    )
    raw_text = message.content[0].text.strip()

    return _parse_vision_response(raw_text)


def _parse_vision_response(raw_text: str) -> ExtractionResult:
    """Parse and validate the JSON payload returned by the Vision call."""
    import json

    # Strip accidental markdown fences.
    clean = re.sub(r"^```[a-z]*\n?", "", raw_text, flags=re.MULTILINE)
    clean = re.sub(r"\n?```$", "", clean, flags=re.MULTILINE).strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        return ExtractionResult(
            ok=False,
            w2=None,
            source="vision",
            errors=[f"Vision response was not valid JSON: {exc}"],
        )

    # Null-out low-confidence fields before validation.
    _LOW = 0.5
    if (data.get("wages_confidence") or 0) < _LOW:
        data["wages"] = None
    if (data.get("withholding_confidence") or 0) < _LOW:
        data["federal_withholding"] = None

    errors: list[str] = []
    wages_raw = data.get("wages")
    withholding_raw = data.get("federal_withholding")

    if wages_raw is None:
        errors.append("Vision could not extract Box 1 wages with sufficient confidence")
    if withholding_raw is None:
        errors.append(
            "Vision could not extract Box 2 withholding with sufficient confidence"
        )
    if errors:
        return ExtractionResult(ok=False, w2=None, source="vision", errors=errors)

    try:
        wages = Decimal(str(wages_raw))
        withholding = Decimal(str(withholding_raw))
    except InvalidOperation as exc:
        return ExtractionResult(
            ok=False,
            w2=None,
            source="vision",
            errors=[f"Could not convert vision values to Decimal: {exc}"],
        )

    box12_raw: list[dict[str, Any]] = []
    for entry in data.get("box12", []):
        if (entry.get("confidence") or 0) >= _LOW:
            box12_raw.append({"code": entry.get("code", ""), "amount": entry.get("amount")})

    val_errors = _validate(wages, withholding, box12_raw)
    if val_errors:
        return ExtractionResult(ok=False, w2=None, source="vision", errors=val_errors)

    w2 = W2(
        wages=wages,
        federal_withholding=withholding,
        box12=tuple(
            Box12Entry(code=e["code"], amount=Decimal(str(e["amount"])))
            for e in box12_raw
        ),
    )
    confidence = {
        "wages": data.get("wages_confidence", 1.0),
        "federal_withholding": data.get("withholding_confidence", 1.0),
        "box12": min(
            (e.get("confidence", 1.0) for e in data.get("box12", [])), default=1.0
        ),
    }
    return ExtractionResult(ok=True, w2=w2, source="vision", confidence=confidence)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_w2(file_bytes: bytes, content_type: str) -> ExtractionResult:
    """Extract W-2 figures from an uploaded file.

    Step 1: if the file is a PDF, try the pdfplumber text-layer parser.
    Step 2: fall back to Claude Vision for image inputs or when the text layer
            lacks the required fields.

    Returns an ExtractionResult; ``ok=False`` means the file was unreadable or
    failed validation — the caller should fall back to the bundled sample.
    """
    if content_type == "application/pdf":
        result = _extract_text_layer(file_bytes)
        if result is not None:
            return result
        # Text layer absent or incomplete — fall through to Vision.

    return _extract_vision(file_bytes, content_type)
