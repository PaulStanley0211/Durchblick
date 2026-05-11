"""Repository: load all tax_constants rows into a dict of snapshots."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TaxConstant
from app.tax.constants import TaxConstantsSnapshot


def load_tax_constants_by_year(
    session: Session,
) -> dict[int, TaxConstantsSnapshot]:
    """Return all rows from the tax_constants table keyed by year.

    One query; result is small (4-6 entries in practice).
    """
    rows = session.execute(select(TaxConstant)).scalars().all()
    return {
        row.year: TaxConstantsSnapshot(
            year=row.year,
            basiszins=row.basiszins,
            sparerpauschbetrag_eur=row.sparerpauschbetrag_eur,
            teilfreistellung_equity=row.teilfreistellung_equity,
            teilfreistellung_mixed=row.teilfreistellung_mixed,
            capital_gains_rate=row.capital_gains_rate,
            solidaritaetszuschlag_rate=row.solidaritaetszuschlag_rate,
        )
        for row in rows
    }
