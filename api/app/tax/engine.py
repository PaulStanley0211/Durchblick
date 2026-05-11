"""Tax orchestrators for lump-sum and Sparplan scenarios.

Both share a year-by-year body (Vorabpauschale -> Teilfreistellung ->
Sparerpauschbetrag -> Abgeltungsteuer -> Soli -> rounded tax record).
They differ only in how fund value evolves and how Basisertrag is
derived. The private helpers _build_year_record isolates the shared
cascade; the callers handle scenario-specific fund-value and
Basisertrag logic.

Convention: investor pays year-end taxes out of pocket (matching
broker withholding via Freistellungsauftrag). The fund value at sale
is gross; final_after_tax_value = final_gross_value - sum_of_yearly_taxes.

Sparerpauschbetrag is applied per-ETF (per-comparison), framed as
"if this ETF were your only investment". The legally precise
aggregation across multiple holdings is out of scope.
"""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Literal

from app.tax.constants import TaxConstantsSnapshot, lookup_year_with_fallback
from app.tax.outcome import TaxOutcome, VorabpauschaleYear
from app.tax.primitives import (
    apply_sparerpauschbetrag,
    apply_teilfreistellung,
    compute_basisertrag,
    compute_capital_gains_tax,
    compute_solidaritaetszuschlag,
    compute_vorabpauschale,
)


def _round_eur(value: Decimal) -> Decimal:
    """Round to 2 decimal places, banker's rounding (matches broker withholding)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _build_year_record(
    *,
    year: int,
    vorabpauschale: Decimal,
    realized_gain: Decimal,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    constants: TaxConstantsSnapshot,
) -> VorabpauschaleYear:
    """Apply the shared tax-cascade to one year's pre-tax income.

    Returns a VorabpauschaleYear with rounded euro amounts.
    """
    pre_tf_income = vorabpauschale + realized_gain
    taxable_after_tf = apply_teilfreistellung(pre_tf_income, teilfreistellung_class, constants)
    teilfreistellung_eur = pre_tf_income - taxable_after_tf

    after_spb = apply_sparerpauschbetrag(taxable_after_tf, constants.sparerpauschbetrag_eur)
    spb_used = min(taxable_after_tf, constants.sparerpauschbetrag_eur)

    cgt = compute_capital_gains_tax(after_spb, constants.capital_gains_rate)
    soli = compute_solidaritaetszuschlag(cgt, constants.solidaritaetszuschlag_rate)
    total_year_tax = _round_eur(cgt + soli)

    return VorabpauschaleYear(
        year=year,
        vorabpauschale_eur=_round_eur(vorabpauschale),
        realized_gain_eur=_round_eur(realized_gain),
        teilfreistellung_eur=_round_eur(teilfreistellung_eur),
        sparerpauschbetrag_used_eur=_round_eur(spb_used),
        capital_gains_tax_eur=_round_eur(cgt),
        solidaritaetszuschlag_eur=_round_eur(soli),
        total_tax_eur=total_year_tax,
    )


def compute_lump_sum_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    investment_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    """Single lump-sum investment held for horizon_years, sold at the end.

    Year-loop algorithm (lump-sum):
      v_end = v_start * (1 + r)
      basisertrag = v_start * basiszins * 0.7  (12-month hold)
      vorabpauschale = max(0, min(basisertrag, v_end - v_start))
      realized_gain (final year only) = max(0, v_end - investment - sum(prior_vp) - vp_this_year)
      tax cascade: Teilfreistellung -> Sparerpauschbetrag -> Abgeltungsteuer -> Soli
      fund_value advances by v_end (NOT reduced by tax — withholding paid out of pocket)
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be >= 1")
    if investment_eur <= Decimal("0"):
        raise ValueError("investment_eur must be > 0")

    fund_value = investment_eur
    cumulative_tax_paid = Decimal("0")
    history: list[VorabpauschaleYear] = []

    for offset in range(horizon_years):
        year = start_year + offset
        constants = lookup_year_with_fallback(tax_constants_by_year, year)

        v_end = fund_value * (Decimal("1") + annual_return_rate)
        basisertrag = compute_basisertrag(fund_value, constants.basiszins)
        vorabpauschale = compute_vorabpauschale(basisertrag, v_end - fund_value)

        is_final_year = offset == horizon_years - 1
        if is_final_year:
            prior_vp_sum = sum(
                (record.vorabpauschale_eur for record in history),
                start=Decimal("0"),
            )
            realized_gain = max(
                Decimal("0"),
                v_end - investment_eur - prior_vp_sum - vorabpauschale,
            )
        else:
            realized_gain = Decimal("0")

        record = _build_year_record(
            year=year,
            vorabpauschale=vorabpauschale,
            realized_gain=realized_gain,
            teilfreistellung_class=teilfreistellung_class,
            constants=constants,
        )
        history.append(record)
        cumulative_tax_paid += record.total_tax_eur
        fund_value = v_end

    final_gross = _round_eur(fund_value)
    return TaxOutcome(
        scenario="lump_sum",
        teilfreistellung_class=teilfreistellung_class,
        horizon_years=horizon_years,
        start_year=start_year,
        annual_return_rate=annual_return_rate,
        total_invested_eur=investment_eur,
        final_gross_value_eur=final_gross,
        total_tax_paid_eur=_round_eur(cumulative_tax_paid),
        final_after_tax_value_eur=_round_eur(final_gross - cumulative_tax_paid),
        yearly_breakdown=history,
    )


def compute_sparplan_outcome(
    *,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    monthly_contribution_eur: Decimal,
    horizon_years: int,
    annual_return_rate: Decimal,
    start_year: int,
    tax_constants_by_year: dict[int, TaxConstantsSnapshot],
) -> TaxOutcome:
    """Monthly Sparplan held for horizon_years, sold in full at the end.

    Annual aggregation with mid-year convention:
      Each year sums 12 monthly contributions into one annual cohort
      assumed acquired at month 6 (half-year weighting).

    Year-loop algorithm (Sparplan):
      C = monthly_contribution * 12
      v_end = v_start * (1 + r) + C * (1 + r * 0.5)   [mid-year approximation]
      basisertrag_old = v_start * basiszins * 0.7       [full year]
      basisertrag_new = C * basiszins * 0.7 * 6/12      [half year]
      basisertrag = basisertrag_old + basisertrag_new
      realized_year_gain = v_end - v_start - C          [appreciation only]
      vorabpauschale = max(0, min(basisertrag, realized_year_gain))
      realized_gain (final year only) = max(0,
          v_end - total_invested - sum(prior_vp) - vp_this_year)
      tax cascade: same as lump-sum
      fund_value advances by v_end (withholding paid out of pocket)
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be >= 1")
    if monthly_contribution_eur <= Decimal("0"):
        raise ValueError("monthly_contribution_eur must be > 0")

    annual_contribution = monthly_contribution_eur * Decimal("12")
    total_invested = annual_contribution * Decimal(horizon_years)

    fund_value = Decimal("0")
    cumulative_tax_paid = Decimal("0")
    history: list[VorabpauschaleYear] = []

    for offset in range(horizon_years):
        year = start_year + offset
        constants = lookup_year_with_fallback(tax_constants_by_year, year)

        v_end = fund_value * (Decimal("1") + annual_return_rate) + annual_contribution * (
            Decimal("1") + annual_return_rate * Decimal("0.5")
        )

        basisertrag_old = compute_basisertrag(fund_value, constants.basiszins, months_held=12)
        basisertrag_new = compute_basisertrag(
            annual_contribution, constants.basiszins, months_held=6
        )
        basisertrag = basisertrag_old + basisertrag_new
        realized_year_gain = v_end - fund_value - annual_contribution
        vorabpauschale = compute_vorabpauschale(basisertrag, realized_year_gain)

        is_final_year = offset == horizon_years - 1
        if is_final_year:
            prior_vp_sum = sum(
                (record.vorabpauschale_eur for record in history),
                start=Decimal("0"),
            )
            realized_gain = max(
                Decimal("0"),
                v_end - total_invested - prior_vp_sum - vorabpauschale,
            )
        else:
            realized_gain = Decimal("0")

        record = _build_year_record(
            year=year,
            vorabpauschale=vorabpauschale,
            realized_gain=realized_gain,
            teilfreistellung_class=teilfreistellung_class,
            constants=constants,
        )
        history.append(record)
        cumulative_tax_paid += record.total_tax_eur
        fund_value = v_end

    final_gross = _round_eur(fund_value)
    return TaxOutcome(
        scenario="sparplan",
        teilfreistellung_class=teilfreistellung_class,
        horizon_years=horizon_years,
        start_year=start_year,
        annual_return_rate=annual_return_rate,
        total_invested_eur=total_invested,
        final_gross_value_eur=final_gross,
        total_tax_paid_eur=_round_eur(cumulative_tax_paid),
        final_after_tax_value_eur=_round_eur(final_gross - cumulative_tax_paid),
        yearly_breakdown=history,
    )
