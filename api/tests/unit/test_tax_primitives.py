"""Unit tests for the six tax primitives.

Boundary cases per primitive as documented in the design spec §5.
"""

from decimal import Decimal

from app.tax.primitives import (
    apply_sparerpauschbetrag,
    apply_teilfreistellung,
    compute_basisertrag,
    compute_capital_gains_tax,
    compute_solidaritaetszuschlag,
    compute_vorabpauschale,
)
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026

C_2026 = TAX_CONSTANTS_2023_2026[2026]


# --- compute_basisertrag ---


def test_basisertrag_full_year() -> None:
    # 10000 * 0.025 * 0.7 * 12/12 = 175.00
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=12)
    assert result == Decimal("175.0000")


def test_basisertrag_half_year() -> None:
    # 10000 * 0.025 * 0.7 * 6/12 = 87.50
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=6)
    assert result == Decimal("87.5000")


def test_basisertrag_zero_months_held() -> None:
    result = compute_basisertrag(Decimal("10000"), Decimal("0.025"), months_held=0)
    assert result == Decimal("0")


def test_basisertrag_zero_basiszins() -> None:
    result = compute_basisertrag(Decimal("10000"), Decimal("0"), months_held=12)
    assert result == Decimal("0")


def test_basisertrag_zero_fund_value() -> None:
    result = compute_basisertrag(Decimal("0"), Decimal("0.025"), months_held=12)
    assert result == Decimal("0")


# --- compute_vorabpauschale ---


def test_vorabpauschale_negative_realized_return_clamps_to_zero() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("-50"),
    )
    assert result == Decimal("0")


def test_vorabpauschale_realized_return_below_basisertrag() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("100"),
    )
    assert result == Decimal("100")


def test_vorabpauschale_realized_return_above_basisertrag() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("175"),
        realized_return=Decimal("500"),
    )
    assert result == Decimal("175")


def test_vorabpauschale_both_zero() -> None:
    result = compute_vorabpauschale(
        basisertrag=Decimal("0"),
        realized_return=Decimal("0"),
    )
    assert result == Decimal("0")


# --- apply_teilfreistellung ---


def test_teilfreistellung_equity_uses_30_percent() -> None:
    # 1000 * (1 - 0.30) = 700
    result = apply_teilfreistellung(Decimal("1000"), "equity", C_2026)
    assert result == Decimal("700.0000")


def test_teilfreistellung_mixed_uses_15_percent() -> None:
    # 1000 * (1 - 0.15) = 850
    result = apply_teilfreistellung(Decimal("1000"), "mixed", C_2026)
    assert result == Decimal("850.0000")


def test_teilfreistellung_none_returns_full_base() -> None:
    result = apply_teilfreistellung(Decimal("1000"), "none", C_2026)
    assert result == Decimal("1000")


def test_teilfreistellung_zero_input_returns_zero() -> None:
    result = apply_teilfreistellung(Decimal("0"), "equity", C_2026)
    assert result == Decimal("0.0000")


# --- apply_sparerpauschbetrag ---


def test_sparerpauschbetrag_income_below_allowance_returns_zero() -> None:
    result = apply_sparerpauschbetrag(Decimal("500"), Decimal("1000"))
    assert result == Decimal("0")


def test_sparerpauschbetrag_income_equal_to_allowance_returns_zero() -> None:
    result = apply_sparerpauschbetrag(Decimal("1000"), Decimal("1000"))
    assert result == Decimal("0")


def test_sparerpauschbetrag_income_above_allowance_returns_difference() -> None:
    result = apply_sparerpauschbetrag(Decimal("1500"), Decimal("1000"))
    assert result == Decimal("500")


# --- compute_capital_gains_tax ---


def test_capital_gains_tax_applies_rate() -> None:
    # 1000 * 0.25 = 250
    result = compute_capital_gains_tax(Decimal("1000"), Decimal("0.25"))
    assert result == Decimal("250.00")


def test_capital_gains_tax_zero_income_returns_zero() -> None:
    result = compute_capital_gains_tax(Decimal("0"), Decimal("0.25"))
    assert result == Decimal("0.00")


# --- compute_solidaritaetszuschlag ---


def test_soli_applies_rate_to_capital_gains_tax() -> None:
    # 250 * 0.055 = 13.75
    result = compute_solidaritaetszuschlag(Decimal("250"), Decimal("0.055"))
    assert result == Decimal("13.750")


def test_soli_zero_tax_returns_zero() -> None:
    result = compute_solidaritaetszuschlag(Decimal("0"), Decimal("0.055"))
    assert result == Decimal("0.000")
