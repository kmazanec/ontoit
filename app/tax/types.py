"""The tax-domain contract: W2, Answers, TaxResult (ADR-006).

This is the FROZEN shape that the extraction feature (F-02) populates, the tax
engine (F-03) consumes and produces, the PDF filler (F-05) reads, the
observation emitter surfaces, and the test suite asserts against. It is decided
once, here, so concurrent features build against a stable shape.

Money is `Decimal`, never float — tax arithmetic must be exact and reproducible.
`W2` and `Answers` are the engine's inputs; `TaxResult` (with `lines` keyed by
1040 line id, and a human-readable `trace`) is its output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

# The two filing statuses in scope (PRD §4). Single and Married Filing Jointly.
FilingStatus = Literal["single", "mfj"]

# A Box 12 entry: a one/two-letter code plus a dollar amount. Code D (401(k)
# deferral) feeds the Saver's Credit; Code W (HSA) is acknowledged but produces
# no 1040 line (already excluded from Box 1 wages — ADR/PRD R10).
@dataclass(frozen=True)
class Box12Entry:
    code: str
    amount: Decimal


@dataclass(frozen=True)
class W2:
    """The figures extracted from a W-2 that the federal return needs."""

    wages: Decimal  # Box 1
    federal_withholding: Decimal  # Box 2
    box12: tuple[Box12Entry, ...] = ()

    @property
    def retirement_deferral(self) -> Decimal:
        """Sum of Box 12 codes that qualify for the Saver's Credit (D, E, F, G,
        H, S, AA, BB, EE). For the target profile this is the code-D 401(k)."""
        qualifying = {"D", "E", "F", "G", "H", "S", "AA", "BB", "EE"}
        return sum(
            (e.amount for e in self.box12 if e.code in qualifying), Decimal("0")
        )


@dataclass(frozen=True)
class Answers:
    """What the ≤5-question conversation gathers (F-04). Credits are inferred
    from these plus the W-2 — never a separate question (PRD R5)."""

    filing_status: FilingStatus
    dependents: int = 0  # number of qualifying children, for EITC


@dataclass(frozen=True)
class TraceStep:
    """One line of the 'show your work' computation: a label, the value, and a
    plain-language reason. Produced by the engine (F-03), rendered by F-08."""

    label: str
    value: Decimal | None
    explanation: str


@dataclass
class TaxResult:
    """The computed 2025 Form 1040. `lines` maps logical 1040 line ids to values
    for the PDF filler (F-05); the scalar fields are the engine's headline
    numbers; `trace` is the line-by-line reasoning."""

    filing_status: FilingStatus
    wages: Decimal
    agi: Decimal
    standard_deduction: Decimal
    taxable_income: Decimal
    tax_before_credits: Decimal
    savers_credit: Decimal
    eitc: Decimal
    total_credits: Decimal
    total_tax: Decimal
    federal_withholding: Decimal
    total_payments: Decimal
    refund: Decimal  # >0 if owed a refund, else 0
    amount_owed: Decimal  # >0 if balance due, else 0
    lines: dict[str, Decimal] = field(default_factory=dict)
    trace: list[TraceStep] = field(default_factory=list)
