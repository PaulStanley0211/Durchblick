"""Unit tests for TaxOutcome + VorabpauschaleYear models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.tax.outcome import TaxOutcome, VorabpauschaleYear


def _sample_year(year: int = 2026) -> VorabpauschaleYear:
    return VorabpauschaleYear(
        year=year,
        vorabpauschale_eur=Decimal("12.34"),
        realized_gain_eur=Decimal("0"),
        teilfreistellung_eur=Decimal("3.70"),
        sparerpauschbetrag_used_eur=Decimal("8.64"),
        capital_gains_tax_eur=Decimal("0.00"),
        solidaritaetszuschlag_eur=Decimal("0.00"),
        total_tax_eur=Decimal("0.00"),
    )


def _sample_outcome() -> TaxOutcome:
    return TaxOutcome(
        scenario="lump_sum",
        teilfreistellung_class="equity",
        horizon_years=10,
        start_year=2026,
        annual_return_rate=Decimal("0.05"),
        total_invested_eur=Decimal("10000.00"),
        final_gross_value_eur=Decimal("16288.95"),
        total_tax_paid_eur=Decimal("1465.50"),
        final_after_tax_value_eur=Decimal("14823.45"),
        yearly_breakdown=[_sample_year(2026 + i) for i in range(10)],
    )


def test_outcome_round_trips_through_dump_and_validate() -> None:
    original = _sample_outcome()
    serialized = original.model_dump()
    restored = TaxOutcome.model_validate(serialized)
    assert restored == original


def test_outcome_is_frozen() -> None:
    outcome = _sample_outcome()
    with pytest.raises(ValidationError):
        outcome.horizon_years = 99  # pyright: ignore[reportAttributeAccessIssue]


def test_decimal_precision_survives_serialization() -> None:
    original = _sample_outcome()
    serialized = original.model_dump(mode="json")
    restored = TaxOutcome.model_validate(serialized)
    # Precision must be exact, not approximate
    assert restored.final_after_tax_value_eur == Decimal("14823.45")
    assert restored.yearly_breakdown[0].vorabpauschale_eur == Decimal("12.34")
