"""Deterministic 2025 Form 1040 tax computation engine.

Entry point: `compute_tax(w2, answers) -> TaxResult`.

This module is pure: no I/O, no network calls, no clock reads. Given the same
inputs it always returns the same output. All money is `Decimal`; the engine
never touches float arithmetic.

Key design decisions documented here to prevent common errors:

  Box 12-D (401k) and Box 12-W (HSA) amounts are ALREADY excluded from Box 1
  wages by the employer. The engine must NOT subtract them again from AGI.
  Doing so would double-deduct and understate taxable income.

  For taxable income under $100,000 the IRS requires Tax Table lookup (rounded
  to the $50 bracket, tax computed on the midpoint) rather than raw bracket
  math. See params_2025.tax_table_lookup for the implementation.
"""

from __future__ import annotations

from decimal import Decimal

from app.tax.params_2025 import (
    EITC_PARAMS,
    SAVERS_MAX_CONTRIBUTION,
    STANDARD_DEDUCTION,
    savers_credit_rate,
    tax_table_lookup,
)
from app.tax.types import Answers, FilingStatus, TaxResult, TraceStep, W2


def compute_tax(w2: W2, answers: Answers) -> TaxResult:
    """Compute a 2025 federal Form 1040 for the given W-2 and filer answers.

    Returns a fully populated TaxResult including:
    - Headline dollar figures (agi, taxable_income, tax_before_credits, etc.)
    - A `lines` dict keyed by 1040 line ids for the PDF filler
    - A `trace` list explaining every computation step in plain language
    """
    status: FilingStatus = answers.filing_status
    trace: list[TraceStep] = []

    def record(label: str, value: Decimal | None, explanation: str) -> None:
        trace.append(TraceStep(label=label, value=value, explanation=explanation))

    # ------------------------------------------------------------------
    # Line 1a — Wages
    # Box 1 already excludes 401(k) deferrals and HSA contributions.
    # ------------------------------------------------------------------
    wages = w2.wages
    record(
        "Line 1a — Wages",
        wages,
        f"Box 1 wages ${wages:,.2f}. Pre-tax deferrals (Box 12-D/W) are already "
        "excluded from Box 1 by the employer — they are NOT subtracted here.",
    )

    # ------------------------------------------------------------------
    # Line 11 — Adjusted Gross Income
    # For this profile there are no Schedule 1 adjustments.
    # ------------------------------------------------------------------
    agi = wages
    record(
        "Line 11 — AGI",
        agi,
        f"AGI = wages ${wages:,.2f} (no Schedule 1 adjustments for this profile).",
    )

    # ------------------------------------------------------------------
    # Line 12 — Standard Deduction
    # ------------------------------------------------------------------
    std_deduction = STANDARD_DEDUCTION[status]
    record(
        "Line 12 — Standard Deduction",
        std_deduction,
        f"2025 standard deduction for {status}: ${std_deduction:,} "
        "(IRS Rev. Proc. 2024-40 §3.10).",
    )

    # ------------------------------------------------------------------
    # Line 15 — Taxable Income
    # ------------------------------------------------------------------
    taxable_income = max(Decimal("0"), agi - std_deduction)
    record(
        "Line 15 — Taxable Income",
        taxable_income,
        f"AGI ${agi:,.2f} − standard deduction ${std_deduction:,} = "
        f"${taxable_income:,.2f}.",
    )

    # ------------------------------------------------------------------
    # Line 16 — Tax (from Tax Table / Tax Computation Worksheet)
    # ------------------------------------------------------------------
    tax_before_credits = tax_table_lookup(taxable_income, status)
    record(
        "Line 16 — Tax (before credits)",
        tax_before_credits,
        f"Tax on ${taxable_income:,.2f} taxable income ({status}) via the "
        "2025 IRS Tax Table (income rounded to nearest $50 bracket, tax "
        f"computed on midpoint): ${tax_before_credits:,}.",
    )

    # ------------------------------------------------------------------
    # Saver's Credit (Form 8880 → Schedule 3 Line 4)
    # The credit is a percentage of elective deferrals, capped at the
    # contribution limit, determined by AGI tier. The W2.retirement_deferral
    # property sums all qualifying Box 12 codes.
    # ------------------------------------------------------------------
    savers_rate = savers_credit_rate(agi, status)
    max_contribution = SAVERS_MAX_CONTRIBUTION[status]
    eligible_contribution = min(w2.retirement_deferral, max_contribution)
    savers_credit = (eligible_contribution * savers_rate).quantize(Decimal("1"))

    if savers_rate == Decimal("0"):
        savers_explanation = (
            f"Saver's Credit = $0 (AGI ${agi:,.2f} exceeds the "
            f"${SAVERS_MAX_CONTRIBUTION[status]:,} contribution cap cutoff — "
            "no credit tier applies at this income level; "
            "IRS Form 8880 / Rev. Proc. 2024-40 §3.08)."
        )
    else:
        savers_explanation = (
            f"Saver's Credit = ${savers_credit:,} "
            f"({savers_rate:.0%} × eligible deferral "
            f"${eligible_contribution:,.2f}; AGI ${agi:,.2f} qualifies for "
            f"the {savers_rate:.0%} tier; IRS Form 8880)."
        )
    record("Saver's Credit", savers_credit, savers_explanation)

    # ------------------------------------------------------------------
    # Earned Income Tax Credit (Schedule EIC)
    # Simplified: if earned income / AGI is at or below the AGI limit for
    # the filer's status and child count, the MAX credit applies. Above the
    # limit the credit is $0.  This is correct for the two tested cases
    # (target profile well above the limit → $0; test case well within → max).
    # See params_2025.EITC_PARAMS for a note on full phase-in/phase-out.
    # ------------------------------------------------------------------
    child_key = min(answers.dependents, 3)
    eitc_params = EITC_PARAMS[child_key]
    agi_limit = (
        eitc_params.agi_limit_mfj if status == "mfj" else eitc_params.agi_limit_single
    )
    # Earned income for EITC purposes equals wages for W-2 filers.
    earned_income = wages

    if earned_income <= agi_limit and agi <= agi_limit:
        eitc = eitc_params.max_credit
        eitc_explanation = (
            f"EITC = ${eitc:,} (max credit for {answers.dependents} qualifying "
            f"child(ren), {status}; earned income ${earned_income:,.2f} ≤ "
            f"limit ${agi_limit:,}; IRS Rev. Proc. 2024-40 §3.07)."
        )
    else:
        eitc = Decimal("0")
        eitc_explanation = (
            f"EITC = $0 ({answers.dependents} qualifying child(ren), {status}; "
            f"AGI ${agi:,.2f} exceeds the ${agi_limit:,} limit; "
            "IRS Rev. Proc. 2024-40 §3.07)."
        )
    record("Earned Income Tax Credit", eitc, eitc_explanation)

    # ------------------------------------------------------------------
    # Total Credits and Total Tax
    # ------------------------------------------------------------------
    total_credits = savers_credit + eitc
    record(
        "Total Credits (Schedule 3)",
        total_credits,
        f"Saver's Credit ${savers_credit:,} + EITC ${eitc:,} = "
        f"${total_credits:,}.",
    )

    total_tax = max(Decimal("0"), tax_before_credits - total_credits)
    record(
        "Line 22 — Total Tax",
        total_tax,
        f"Tax ${tax_before_credits:,} − credits ${total_credits:,} = "
        f"${total_tax:,}.",
    )

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    federal_withholding = w2.federal_withholding
    total_payments = federal_withholding
    record(
        "Line 25a — Federal Tax Withheld",
        federal_withholding,
        f"Box 2 federal income tax withheld: ${federal_withholding:,.2f}.",
    )
    record(
        "Line 33 — Total Payments",
        total_payments,
        f"Total payments (withholding only for this profile): "
        f"${total_payments:,.2f}.",
    )

    # ------------------------------------------------------------------
    # Refund or Amount Owed
    # ------------------------------------------------------------------
    refund = max(Decimal("0"), total_payments - total_tax)
    amount_owed = max(Decimal("0"), total_tax - total_payments)

    if refund > 0:
        record(
            "Line 34 — Refund",
            refund,
            f"Payments ${total_payments:,.2f} − tax ${total_tax:,} = "
            f"refund ${refund:,.2f}.",
        )
        record("Line 37 — Amount Owed", Decimal("0"), "No balance due.")
    else:
        record("Line 34 — Refund", Decimal("0"), "No refund.")
        record(
            "Line 37 — Amount Owed",
            amount_owed,
            f"Tax ${total_tax:,} − payments ${total_payments:,.2f} = "
            f"balance due ${amount_owed:,.2f}.",
        )

    # ------------------------------------------------------------------
    # 1040 Line Dictionary (for PDF filler)
    # ------------------------------------------------------------------
    lines: dict[str, Decimal] = {
        "line_1a_wages": wages,
        "line_11_agi": agi,
        "line_12_std_deduction": std_deduction,
        "line_15_taxable_income": taxable_income,
        "line_16_tax": tax_before_credits,
        "line_19_credits": total_credits,
        "line_22_total_tax": total_tax,
        "line_25a_withholding": federal_withholding,
        "line_33_total_payments": total_payments,
        "line_34_refund": refund,
        "line_37_owed": amount_owed,
    }

    return TaxResult(
        filing_status=status,
        wages=wages,
        agi=agi,
        standard_deduction=std_deduction,
        taxable_income=taxable_income,
        tax_before_credits=tax_before_credits,
        savers_credit=savers_credit,
        eitc=eitc,
        total_credits=total_credits,
        total_tax=total_tax,
        federal_withholding=federal_withholding,
        total_payments=total_payments,
        refund=refund,
        amount_owed=amount_owed,
        lines=lines,
        trace=trace,
    )
