"""Tax-constants snapshot + future-year fallback resolution."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxConstantsSnapshot:
    """Immutable per-year tax-constants record.

    Mirrors a row of the tax_constants table. The tax module never
    touches the SQLAlchemy model directly; the repository builds
    one of these per row.
    """

    year: int
    basiszins: Decimal
    sparerpauschbetrag_eur: Decimal
    teilfreistellung_equity: Decimal
    teilfreistellung_mixed: Decimal
    capital_gains_rate: Decimal
    solidaritaetszuschlag_rate: Decimal


def lookup_year_with_fallback(
    by_year: dict[int, TaxConstantsSnapshot],
    year: int,
) -> TaxConstantsSnapshot:
    """Return the snapshot for `year`. If absent, return the latest year present.

    Raises ValueError if the dict is empty.
    """
    if year in by_year:
        return by_year[year]
    if not by_year:
        raise ValueError("tax constants dict is empty")
    return by_year[max(by_year)]
