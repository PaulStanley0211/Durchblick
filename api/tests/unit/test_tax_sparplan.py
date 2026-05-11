"""Golden-value tests for compute_sparplan_outcome.

Sparplan uses annual aggregation with mid-year convention: each year
sums 12 monthly contributions into one annual cohort treated as if
acquired at month 6. Goldens derived by the same hand-trace approach
as lump-sum.
"""

from decimal import Decimal

import pytest

from app.tax.engine import compute_sparplan_outcome
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_one_year_5_percent_equity_2026() -> None:
    """100/month over 1 year at 5%, equity ETF.

    Single-year Sparplan stresses the mid-year split.

    Year 2026 (final):
      C = 100 * 12 = 1200
      v_start = 0
      v_end = 0 * 1.05 + 1200 * (1 + 0.05 * 0.5) = 1230.00
      basisertrag_old = 0 * 0.025 * 0.7 = 0
      basisertrag_new = 1200 * 0.025 * 0.7 * 6/12 = 10.50
      basisertrag = 10.50
      realized_year_gain = 1230 - 0 - 1200 = 30
      vorabpauschale = min(10.50, 30) = 10.50
      realized_gain = max(0, 1230 - 1200 - 0 - 10.50) = 19.50
      taxable_after_tf = (10.50 + 19.50) * 0.70 = 21.00
      after_spb = max(0, 21 - 1000) = 0
      year_tax = 0.00
      final_after_tax = 1230.00
    """
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=1,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.scenario == "sparplan"
    assert outcome.total_invested_eur == Decimal("1200")
    assert outcome.final_gross_value_eur == Decimal("1230.00")
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("1230.00")


def test_ten_year_5_percent_equity_2026_structural_invariants() -> None:
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=10,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_invested_eur == Decimal("12000")
    assert outcome.final_gross_value_eur > outcome.total_invested_eur
    assert outcome.final_after_tax_value_eur <= outcome.final_gross_value_eur
    assert outcome.final_after_tax_value_eur > outcome.total_invested_eur
    assert len(outcome.yearly_breakdown) == 10


def test_zero_return_produces_no_tax() -> None:
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("100"),
        horizon_years=10,
        annual_return_rate=Decimal("0"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_gross_value_eur == Decimal("12000")
    assert outcome.final_after_tax_value_eur == Decimal("12000")


def test_zero_monthly_contribution_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_sparplan_outcome(
            teilfreistellung_class="equity",
            monthly_contribution_eur=Decimal("0"),
            horizon_years=10,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )


def test_horizon_zero_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_sparplan_outcome(
            teilfreistellung_class="equity",
            monthly_contribution_eur=Decimal("100"),
            horizon_years=0,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )


def test_prior_year_vorabpauschale_is_credited_against_final_sale() -> None:
    """Property check: total tax across all years matches the per-year
    breakdown sum, AND the final-year realized_gain_eur is reduced by
    prior years' vorabpauschale_eur sum."""
    outcome = compute_sparplan_outcome(
        teilfreistellung_class="equity",
        monthly_contribution_eur=Decimal("500"),
        horizon_years=10,
        annual_return_rate=Decimal("0.07"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    sum_of_year_taxes = sum(
        (year.total_tax_eur for year in outcome.yearly_breakdown),
        start=Decimal("0"),
    )
    assert outcome.total_tax_paid_eur == sum_of_year_taxes
    final_year = outcome.yearly_breakdown[-1]
    prior_vp_sum = sum(
        (year.vorabpauschale_eur for year in outcome.yearly_breakdown[:-1]),
        start=Decimal("0"),
    )
    assert final_year.realized_gain_eur >= Decimal("0")
    raw_lifetime_gain = outcome.final_gross_value_eur - outcome.total_invested_eur
    accounted = final_year.realized_gain_eur + prior_vp_sum + final_year.vorabpauschale_eur
    assert accounted == raw_lifetime_gain
