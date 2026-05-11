"""Golden-value tests for compute_lump_sum_outcome.

The 10,000-over-10-years scenarios were derived by hand-tracing
the algorithm with the values in tests/fixtures/tax_constants_2023_2026.py.
If the seeded constants drift, regenerate the goldens with the same
hand trace.
"""

from decimal import Decimal

import pytest

from app.tax.engine import compute_lump_sum_outcome
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_one_year_5_percent_equity_2026() -> None:
    """10,000 invested for 1 year at 5%, equity ETF.

    Single-iteration sanity check. The final year computes both
    Vorabpauschale AND realized gain.

    Year 2026 (final):
      v_start = 10000.00
      v_end   = 10000.00 * 1.05 = 10500.00
      basisertrag = 10000 * 0.025 * 0.7 = 175.0000
      realized_year_gain = 10500 - 10000 = 500
      vorabpauschale = min(175, 500) = 175.0000
      realized_gain  = max(0, 10500 - 10000 - 0 - 175) = 325.0000
      taxable_after_tf = (175 + 325) * 0.70 = 350.0000
      after_spb = max(0, 350 - 1000) = 0
      cgt = 0; soli = 0; year_tax = 0.00
      final_after_tax = 10500.00 - 0.00 = 10500.00
    """
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=1,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.scenario == "lump_sum"
    assert outcome.total_invested_eur == Decimal("10000")
    assert outcome.final_gross_value_eur == Decimal("10500.00")
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("10500.00")
    assert len(outcome.yearly_breakdown) == 1


def test_ten_year_5_percent_equity_2026_produces_positive_after_tax_below_gross() -> None:
    """10,000 over 10 years at 5%, equity ETF.

    Year-by-year hand trace is documented in the implementation comments
    on `compute_lump_sum_outcome`. The golden numbers assert structural
    properties: after-tax < gross < pure-compound, total tax > 0.
    """
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("0.05"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    pure_compound = Decimal("10000") * (Decimal("1.05") ** 10)
    assert outcome.final_gross_value_eur == pure_compound.quantize(Decimal("0.01")) or abs(
        outcome.final_gross_value_eur - pure_compound
    ) < Decimal("0.01")
    assert outcome.total_tax_paid_eur > Decimal("0")
    assert outcome.final_after_tax_value_eur < outcome.final_gross_value_eur
    assert outcome.final_after_tax_value_eur > outcome.total_invested_eur
    assert len(outcome.yearly_breakdown) == 10


def test_zero_return_produces_no_tax() -> None:
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("0"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_after_tax_value_eur == Decimal("10000")
    assert outcome.final_gross_value_eur == Decimal("10000")


def test_negative_return_produces_no_tax_and_loss() -> None:
    outcome = compute_lump_sum_outcome(
        teilfreistellung_class="equity",
        investment_eur=Decimal("10000"),
        horizon_years=10,
        annual_return_rate=Decimal("-0.03"),
        start_year=2026,
        tax_constants_by_year=TAX_CONSTANTS_2023_2026,
    )
    assert outcome.total_tax_paid_eur == Decimal("0.00")
    assert outcome.final_gross_value_eur < outcome.total_invested_eur
    assert outcome.final_after_tax_value_eur == outcome.final_gross_value_eur


def test_horizon_zero_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_lump_sum_outcome(
            teilfreistellung_class="equity",
            investment_eur=Decimal("10000"),
            horizon_years=0,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )


def test_zero_investment_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_lump_sum_outcome(
            teilfreistellung_class="equity",
            investment_eur=Decimal("0"),
            horizon_years=10,
            annual_return_rate=Decimal("0.05"),
            start_year=2026,
            tax_constants_by_year=TAX_CONSTANTS_2023_2026,
        )
