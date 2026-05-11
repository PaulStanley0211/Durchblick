"""Integration test: verify Alembic schema + tax_constants seed.

Runs against the DATABASE_URL from the environment (api/.env locally,
the postgres service container in CI). Expects migrations to have been
applied via `alembic upgrade head` before the test runs.
"""

import pytest
from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from scripts.seed_tax_constants import TAX_CONSTANTS, seed

EXPECTED_TABLES = {"comparisons", "etfs", "prices", "tax_constants"}
EXPECTED_YEARS = {row["year"] for row in TAX_CONSTANTS}


@pytest.fixture(scope="module")
def engine() -> Engine:
    return create_engine(get_settings().database_url)


def test_all_phase_one_tables_exist(engine: Engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name IN ('etfs', 'prices', 'tax_constants', 'comparisons')"
            )
        )
        tables = {row[0] for row in result}
    assert tables == EXPECTED_TABLES


def test_tax_constants_seeded_for_all_expected_years(engine: Engine) -> None:
    seed()  # idempotent upsert
    with engine.connect() as conn:
        result = conn.execute(text("SELECT year FROM tax_constants ORDER BY year"))
        years = {row[0] for row in result}
    assert EXPECTED_YEARS.issubset(years)
