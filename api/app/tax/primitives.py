"""Six pure tax primitives. No I/O, no side effects, Decimal only.

Each function captures one rule (or one piece of a rule) from the
German tax code. Vorabpauschale (§18 InvStG) is split into
compute_basisertrag and compute_vorabpauschale so the Sparplan
orchestrator can sum two Basiserträge (old principal full year,
new contributions half year) before clamping.
"""

from decimal import Decimal
from typing import Literal

from app.tax.constants import TaxConstantsSnapshot


def compute_basisertrag(
    fund_value: Decimal,
    basiszins: Decimal,
    months_held: int = 12,
) -> Decimal:
    """Basisertrag: fund_value * basiszins * 0.7, pro-rated by months_held/12."""
    return fund_value * basiszins * Decimal("0.7") * Decimal(months_held) / Decimal("12")


def compute_vorabpauschale(
    basisertrag: Decimal,
    realized_return: Decimal,
) -> Decimal:
    """Vorabpauschale = max(0, min(basisertrag, realized_return))."""
    return max(Decimal("0"), min(basisertrag, realized_return))


def apply_teilfreistellung(
    taxable_base: Decimal,
    teilfreistellung_class: Literal["equity", "mixed", "none"],
    constants: TaxConstantsSnapshot,
) -> Decimal:
    """Return taxable_base after the equity/mixed/none exemption."""
    rate = {
        "equity": constants.teilfreistellung_equity,
        "mixed": constants.teilfreistellung_mixed,
        "none": Decimal("0"),
    }[teilfreistellung_class]
    return taxable_base * (Decimal("1") - rate)


def apply_sparerpauschbetrag(
    post_teilfreistellung_income: Decimal,
    allowance: Decimal,
) -> Decimal:
    """Return income reduced by the year's allowance, floored at 0."""
    return max(Decimal("0"), post_teilfreistellung_income - allowance)


def compute_capital_gains_tax(
    taxable_income: Decimal,
    capital_gains_rate: Decimal,
) -> Decimal:
    """Flat-rate Abgeltungsteuer on the post-allowance base."""
    return taxable_income * capital_gains_rate


def compute_solidaritaetszuschlag(
    capital_gains_tax: Decimal,
    solidaritaetszuschlag_rate: Decimal,
) -> Decimal:
    """Surcharge on capital gains tax (not on income)."""
    return capital_gains_tax * solidaritaetszuschlag_rate
