"""Hand-built fixture mirroring api/scripts/seed_tax_constants.py.

Used by unit tests to construct an in-memory dict of snapshots
without a DB roundtrip. Keep in sync with seed_tax_constants.py
if the seeded values change.
"""

from decimal import Decimal

from app.tax.constants import TaxConstantsSnapshot

TAX_CONSTANTS_2023_2026: dict[int, TaxConstantsSnapshot] = {
    2023: TaxConstantsSnapshot(
        year=2023,
        basiszins=Decimal("0.0255"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2024: TaxConstantsSnapshot(
        year=2024,
        basiszins=Decimal("0.0229"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2025: TaxConstantsSnapshot(
        year=2025,
        basiszins=Decimal("0.0253"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
    2026: TaxConstantsSnapshot(
        year=2026,
        basiszins=Decimal("0.0250"),
        sparerpauschbetrag_eur=Decimal("1000.00"),
        teilfreistellung_equity=Decimal("0.3000"),
        teilfreistellung_mixed=Decimal("0.1500"),
        capital_gains_rate=Decimal("0.2500"),
        solidaritaetszuschlag_rate=Decimal("0.0550"),
    ),
}
