"""The bundled sample W-2 (R3 — the one-click fallback).

A judge needs a guaranteed clean run even if an upload is unreadable, so a
realistic fake W-2 ships in `assets/sample-w2.pdf` and its figures are available
with one click. The known box values are recorded here so the skeleton is
self-contained; iteration 02 (F-02) replaces this with real extraction of an
uploaded file (pdfplumber -> Claude Vision) — the sample fallback then guards
that path.

Figures are the sample filer's actual W-2 boxes (Elizabeth A. Darling):
Box 1 wages 44,629.35, Box 2 federal withholding 7,631.62, Box 12-E retirement
deferral 4,107.00, Box 12-W HSA 1,500.00.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SAMPLE_PDF_PATH = Path(__file__).resolve().parent.parent / "assets" / "sample-w2.pdf"

SAMPLE_W2: dict[str, Any] = {
    "wages": 44629.35,  # Box 1
    "federal_withholding": 7631.62,  # Box 2
    "box12": [
        # Code E (403(b) elective deferral) on the actual sample W-2 — a
        # qualifying contribution for the Saver's Credit, same as a 401(k).
        {"code": "E", "amount": 4107.00},
        {"code": "W", "amount": 1500.00},  # HSA (pre-tax, no 1040 line)
    ],
    "source": "sample",
}
