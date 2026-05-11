"""Pydantic return types for the tax orchestrators."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class VorabpauschaleYear(BaseModel):
    """Per-year tax record produced by the orchestrator's year loop."""

    model_config = ConfigDict(frozen=True)

    year: int
    vorabpauschale_eur: Decimal
    realized_gain_eur: Decimal
    teilfreistellung_eur: Decimal
    sparerpauschbetrag_used_eur: Decimal
    capital_gains_tax_eur: Decimal
    solidaritaetszuschlag_eur: Decimal
    total_tax_eur: Decimal


class TaxOutcome(BaseModel):
    """Result of one tax simulation: lump-sum or Sparplan."""

    model_config = ConfigDict(frozen=True)

    scenario: Literal["lump_sum", "sparplan"]
    teilfreistellung_class: Literal["equity", "mixed", "none"]
    horizon_years: int
    start_year: int
    annual_return_rate: Decimal

    total_invested_eur: Decimal
    final_gross_value_eur: Decimal
    total_tax_paid_eur: Decimal
    final_after_tax_value_eur: Decimal

    yearly_breakdown: list[VorabpauschaleYear]
