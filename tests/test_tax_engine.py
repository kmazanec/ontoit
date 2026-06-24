"""Golden tests for the 2025 federal tax engine (F-03).

All assertions are at the public boundary: compute_tax(W2, Answers) -> TaxResult.
No internal functions are tested directly.

Golden profile (AC6):
  W-2: wages $44,629.35, withholding $7,631.62, Box12-D $4,107.00, Box12-W $1,500.00
  Answers: Single, 0 dependents
  Expected: taxable_income $28,879.35, tax ≈ $3,227, refund ≈ $4,405,
            savers_credit $0 (AGI exceeds $39,500 limit), eitc $0 (exceeds $19,104 limit)
"""

from decimal import Decimal

import pytest

from app.tax.engine import compute_tax
from app.tax.types import Answers, Box12Entry, TaxResult, W2


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def golden_w2() -> W2:
    """The target-profile W-2: Single filer, moderate income, 401k + HSA."""
    return W2(
        wages=Decimal("44629.35"),
        federal_withholding=Decimal("7631.62"),
        box12=(
            Box12Entry(code="D", amount=Decimal("4107.00")),
            Box12Entry(code="W", amount=Decimal("1500.00")),
        ),
    )


@pytest.fixture
def single_answers() -> Answers:
    return Answers(filing_status="single", dependents=0)


@pytest.fixture
def mfj_answers() -> Answers:
    return Answers(filing_status="mfj", dependents=0)


# ---------------------------------------------------------------------------
# AC6 — Golden single-filer numbers
# ---------------------------------------------------------------------------

class TestAC6GoldenSingle:
    def test_taxable_income(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        # wages $44,629.35 − standard deduction $15,750 = $28,879.35
        assert result.taxable_income == Decimal("28879.35")

    def test_tax_within_one_dollar(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        # Tax Table on $28,879.35 → bracket [$28,850, $28,900), midpoint $28,875
        # Tax on $28,875: 10% × $11,925 + 12% × ($28,875 − $11,925) = $1,192.50 + $2,034 = $3,226.50 → $3,227
        assert abs(result.tax_before_credits - Decimal("3227")) <= Decimal("1")

    def test_savers_credit_zero(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        # AGI $44,629.35 > $39,500 Single Saver's cutoff → $0
        assert result.savers_credit == Decimal("0")

    def test_eitc_zero(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        # AGI $44,629.35 > $19,104 Single/0-kids EITC limit → $0
        assert result.eitc == Decimal("0")

    def test_refund_within_one_dollar(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        # withholding $7,631.62 − tax $3,227 ≈ $4,404.62 → refund ≈ $4,405
        assert abs(result.refund - Decimal("4405")) <= Decimal("1")

    def test_required_lines_present(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        required = {
            "line_1a_wages",
            "line_11_agi",
            "line_12_std_deduction",
            "line_15_taxable_income",
            "line_16_tax",
            "line_19_credits",
            "line_22_total_tax",
            "line_25a_withholding",
            "line_33_total_payments",
            "line_34_refund",
            "line_37_owed",
        }
        assert required.issubset(result.lines.keys())

    def test_lines_values_match_fields(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        assert result.lines["line_1a_wages"] == result.wages
        assert result.lines["line_15_taxable_income"] == result.taxable_income
        assert result.lines["line_34_refund"] == result.refund


# ---------------------------------------------------------------------------
# AC7 — MFJ produces a larger deduction and different (larger) refund
# ---------------------------------------------------------------------------

class TestAC7MFJ:
    def test_standard_deduction_is_31500(self, golden_w2: W2, mfj_answers: Answers) -> None:
        result = compute_tax(golden_w2, mfj_answers)
        assert result.standard_deduction == Decimal("31500")

    def test_refund_larger_than_single(
        self, golden_w2: W2, single_answers: Answers, mfj_answers: Answers
    ) -> None:
        single = compute_tax(golden_w2, single_answers)
        mfj = compute_tax(golden_w2, mfj_answers)
        # Larger deduction → lower taxable income → lower tax → bigger refund
        assert mfj.refund > single.refund

    def test_taxable_income_lower_than_single(
        self, golden_w2: W2, single_answers: Answers, mfj_answers: Answers
    ) -> None:
        single = compute_tax(golden_w2, single_answers)
        mfj = compute_tax(golden_w2, mfj_answers)
        assert mfj.taxable_income < single.taxable_income


# ---------------------------------------------------------------------------
# AC8 — Saver's Credit: non-zero when AGI is in range; $0 for golden profile
# ---------------------------------------------------------------------------

class TestAC8SaversCredit:
    def test_nonzero_when_agi_within_range(self) -> None:
        # Wages $22,000 → AGI $22,000, standard deduction $15,750
        # Saver's tier: Single ≤ $23,750 → 50% rate
        # retirement_deferral: Box12-D $2,000 (at the cap) → credit = $2,000 × 50% = $1,000
        w2 = W2(
            wages=Decimal("22000"),
            federal_withholding=Decimal("2000"),
            box12=(Box12Entry(code="D", amount=Decimal("2000")),),
        )
        result = compute_tax(w2, Answers(filing_status="single", dependents=0))
        assert result.savers_credit > Decimal("0")
        assert result.savers_credit == Decimal("1000")

    def test_correct_rate_applied(self) -> None:
        # AGI $25,000 falls in the 20% tier ($23,751–$25,500) for Single
        w2 = W2(
            wages=Decimal("25000"),
            federal_withholding=Decimal("2000"),
            box12=(Box12Entry(code="D", amount=Decimal("2000")),),
        )
        result = compute_tax(w2, Answers(filing_status="single", dependents=0))
        # 20% × $2,000 = $400
        assert result.savers_credit == Decimal("400")

    def test_zero_for_golden_profile(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        assert result.savers_credit == Decimal("0")

    def test_contribution_capped_at_2000_single(self) -> None:
        # Even with a $5,000 deferral the credit is calculated on $2,000 max
        w2 = W2(
            wages=Decimal("20000"),
            federal_withholding=Decimal("1000"),
            box12=(Box12Entry(code="D", amount=Decimal("5000")),),
        )
        result = compute_tax(w2, Answers(filing_status="single", dependents=0))
        # AGI $20,000 ≤ $23,750 → 50%; max contribution $2,000 → $1,000
        assert result.savers_credit == Decimal("1000")


# ---------------------------------------------------------------------------
# AC9 — EITC: non-zero MFJ with child; $0 for golden profile
# ---------------------------------------------------------------------------

class TestAC9EITC:
    def test_nonzero_mfj_one_child(self) -> None:
        # MFJ, wages $44,629, 1 child: limit $57,554 — income is under limit
        w2 = W2(
            wages=Decimal("44629"),
            federal_withholding=Decimal("5000"),
        )
        result = compute_tax(w2, Answers(filing_status="mfj", dependents=1))
        assert result.eitc > Decimal("0")
        # Should receive the max credit for 1 child: $4,328
        assert result.eitc == Decimal("4328")

    def test_zero_for_golden_profile(self, golden_w2: W2, single_answers: Answers) -> None:
        result = compute_tax(golden_w2, single_answers)
        assert result.eitc == Decimal("0")

    def test_zero_when_above_limit(self) -> None:
        # Single, 0 kids, $44,629 > $19,104 limit
        w2 = W2(wages=Decimal("44629"), federal_withholding=Decimal("5000"))
        result = compute_tax(w2, Answers(filing_status="single", dependents=0))
        assert result.eitc == Decimal("0")


# ---------------------------------------------------------------------------
# AC11 — Box 12-W HSA does NOT affect taxable income
# ---------------------------------------------------------------------------

class TestAC11HSANotDeducted:
    def test_taxable_income_unchanged_with_hsa(self) -> None:
        # W-2 with HSA entry
        w2_with_hsa = W2(
            wages=Decimal("44629.35"),
            federal_withholding=Decimal("7631.62"),
            box12=(Box12Entry(code="W", amount=Decimal("1500.00")),),
        )
        # Same W-2 without the HSA entry
        w2_without_hsa = W2(
            wages=Decimal("44629.35"),
            federal_withholding=Decimal("7631.62"),
        )
        answers = Answers(filing_status="single", dependents=0)
        result_with = compute_tax(w2_with_hsa, answers)
        result_without = compute_tax(w2_without_hsa, answers)
        # HSA is already excluded from Box 1 wages — taxable income must be identical
        assert result_with.taxable_income == result_without.taxable_income

    def test_hsa_not_in_retirement_deferral(self) -> None:
        # Code W must not count toward Saver's Credit eligibility
        w2 = W2(
            wages=Decimal("22000"),
            federal_withholding=Decimal("1000"),
            box12=(
                Box12Entry(code="W", amount=Decimal("3000")),  # HSA only, no 401k
            ),
        )
        result = compute_tax(w2, Answers(filing_status="single", dependents=0))
        # No qualifying deferral → no Saver's Credit regardless of AGI
        assert result.savers_credit == Decimal("0")


# ---------------------------------------------------------------------------
# Determinism — same inputs always produce equal results
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_double_call_equal(self, golden_w2: W2, single_answers: Answers) -> None:
        r1 = compute_tax(golden_w2, single_answers)
        r2 = compute_tax(golden_w2, single_answers)
        assert r1.taxable_income == r2.taxable_income
        assert r1.tax_before_credits == r2.tax_before_credits
        assert r1.savers_credit == r2.savers_credit
        assert r1.eitc == r2.eitc
        assert r1.total_tax == r2.total_tax
        assert r1.refund == r2.refund
        assert r1.lines == r2.lines

    def test_trace_length_stable(self, golden_w2: W2, single_answers: Answers) -> None:
        r1 = compute_tax(golden_w2, single_answers)
        r2 = compute_tax(golden_w2, single_answers)
        assert len(r1.trace) == len(r2.trace)
