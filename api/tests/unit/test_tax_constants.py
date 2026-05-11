"""Unit tests for TaxConstantsSnapshot + lookup_year_with_fallback."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.tax.constants import lookup_year_with_fallback
from tests.fixtures.tax_constants_2023_2026 import TAX_CONSTANTS_2023_2026


def test_lookup_returns_exact_year_when_present() -> None:
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2024)
    assert snapshot.year == 2024
    assert snapshot.basiszins == Decimal("0.0229")


def test_lookup_future_year_falls_back_to_latest() -> None:
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2030)
    assert snapshot.year == 2026


def test_lookup_past_year_falls_back_to_latest() -> None:
    # Symmetric fallback: past-year case also returns latest.
    snapshot = lookup_year_with_fallback(TAX_CONSTANTS_2023_2026, 2020)
    assert snapshot.year == 2026


def test_lookup_single_row_dict_returns_that_row() -> None:
    only_2026 = {2026: TAX_CONSTANTS_2023_2026[2026]}
    assert lookup_year_with_fallback(only_2026, 2099).year == 2026


def test_lookup_empty_dict_raises_value_error() -> None:
    with pytest.raises(ValueError) as exc:
        lookup_year_with_fallback({}, 2026)
    assert "empty" in str(exc.value).lower()


def test_snapshot_is_frozen() -> None:
    snapshot = TAX_CONSTANTS_2023_2026[2026]
    with pytest.raises(FrozenInstanceError):
        snapshot.basiszins = Decimal("0.99")  # pyright: ignore[reportAttributeAccessIssue]
