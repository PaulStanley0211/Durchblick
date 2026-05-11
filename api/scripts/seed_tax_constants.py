"""Seed the tax_constants table with year-indexed German tax values.

Values are based on official Bundesministerium der Finanzen (BMF)
publications. The Basiszins changes annually; the other values are
codified in the Investmentsteuergesetz (InvStG) and the
Einkommensteuergesetz (EStG) and have been stable since 2023.

These values must be verified against the current BMF publications
before any production use of the tax calculation module (Phase 8).

Idempotent: re-running upserts on the year primary key.

Run with:
    cd api && uv run python -m scripts.seed_tax_constants
"""

from decimal import Decimal

from sqlalchemy import create_engine, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import TaxConstant

TAX_CONSTANTS: list[dict[str, int | Decimal]] = [
    {
        "year": 2023,
        "basiszins": Decimal("0.0255"),
        "sparerpauschbetrag_eur": Decimal("1000.00"),
        "teilfreistellung_equity": Decimal("0.3000"),
        "teilfreistellung_mixed": Decimal("0.1500"),
        "capital_gains_rate": Decimal("0.2500"),
        "solidaritaetszuschlag_rate": Decimal("0.0550"),
    },
    {
        "year": 2024,
        "basiszins": Decimal("0.0229"),
        "sparerpauschbetrag_eur": Decimal("1000.00"),
        "teilfreistellung_equity": Decimal("0.3000"),
        "teilfreistellung_mixed": Decimal("0.1500"),
        "capital_gains_rate": Decimal("0.2500"),
        "solidaritaetszuschlag_rate": Decimal("0.0550"),
    },
    {
        "year": 2025,
        "basiszins": Decimal("0.0253"),
        "sparerpauschbetrag_eur": Decimal("1000.00"),
        "teilfreistellung_equity": Decimal("0.3000"),
        "teilfreistellung_mixed": Decimal("0.1500"),
        "capital_gains_rate": Decimal("0.2500"),
        "solidaritaetszuschlag_rate": Decimal("0.0550"),
    },
    {
        "year": 2026,
        # Placeholder: BMF typically publishes the Basiszins in January.
        # Update this value once the official 2026 figure is available.
        "basiszins": Decimal("0.0250"),
        "sparerpauschbetrag_eur": Decimal("1000.00"),
        "teilfreistellung_equity": Decimal("0.3000"),
        "teilfreistellung_mixed": Decimal("0.1500"),
        "capital_gains_rate": Decimal("0.2500"),
        "solidaritaetszuschlag_rate": Decimal("0.0550"),
    },
]


def seed() -> int:
    """Upsert TAX_CONSTANTS rows. Returns the number of rows written."""
    settings = get_settings()
    engine = create_engine(settings.database_url)

    with Session(engine) as session:
        stmt = insert(TaxConstant).values(TAX_CONSTANTS)
        stmt = stmt.on_conflict_do_update(
            index_elements=["year"],
            set_={
                "basiszins": stmt.excluded.basiszins,
                "sparerpauschbetrag_eur": stmt.excluded.sparerpauschbetrag_eur,
                "teilfreistellung_equity": stmt.excluded.teilfreistellung_equity,
                "teilfreistellung_mixed": stmt.excluded.teilfreistellung_mixed,
                "capital_gains_rate": stmt.excluded.capital_gains_rate,
                "solidaritaetszuschlag_rate": stmt.excluded.solidaritaetszuschlag_rate,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        session.commit()

    return len(TAX_CONSTANTS)


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} tax_constants rows.")
