"""Integration test: load_tax_constants_by_year against Docker Postgres.

Requires `alembic upgrade head` and `scripts.seed_tax_constants` to
have populated the DB. The autouse fixture seeds before each test
so the order with other integration tests does not matter.
"""

from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine

from app.config import get_settings
from app.repositories.tax_constants import load_tax_constants_by_year
from app.tax.constants import TaxConstantsSnapshot
from scripts.seed_tax_constants import seed as seed_tax_constants


@pytest.fixture(scope="module")
def engine() -> Engine:
    return create_engine(get_settings().database_url)


@pytest.fixture(autouse=True)
def _seed() -> None:
    seed_tax_constants()


def test_load_returns_dict_of_snapshots(engine: Engine) -> None:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        result = load_tax_constants_by_year(session)
    assert isinstance(result, dict)
    expected_years = {2023, 2024, 2025, 2026}
    assert expected_years.issubset(set(result.keys()))
    for snapshot in result.values():
        assert isinstance(snapshot, TaxConstantsSnapshot)


def test_load_preserves_decimal_values(engine: Engine) -> None:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        result = load_tax_constants_by_year(session)
    snapshot_2024 = result[2024]
    assert snapshot_2024.basiszins == Decimal("0.0229")
    assert snapshot_2024.sparerpauschbetrag_eur == Decimal("1000.00")
    assert snapshot_2024.teilfreistellung_equity == Decimal("0.3000")
    assert snapshot_2024.capital_gains_rate == Decimal("0.2500")
    assert snapshot_2024.solidaritaetszuschlag_rate == Decimal("0.0550")
