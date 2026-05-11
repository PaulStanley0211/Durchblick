"""Integration test: seed_etfs against a real Postgres database.

Each test truncates the etfs table first so the seed runs against a
known state. Requires `alembic upgrade head` to have been applied.
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from scripts.seed_etfs import seed

FIXTURE = Path(__file__).parent.parent / "fixtures" / "etfs_seed_sample.yaml"


@pytest.fixture(scope="module")
def engine() -> Engine:
    return create_engine(get_settings().database_url)


@pytest.fixture(autouse=True)
def _truncate_etfs(engine: Engine) -> None:
    with engine.begin() as conn:
        # prices has FK to etfs; truncate it first
        conn.execute(text("TRUNCATE TABLE prices, etfs RESTART IDENTITY CASCADE"))


def test_seed_inserts_all_rows_from_fixture(engine: Engine) -> None:
    written = seed(yaml_path=FIXTURE)
    assert written == 3
    with engine.connect() as conn:
        result = conn.execute(text("SELECT isin, name FROM etfs ORDER BY isin"))
        rows = list(result)
    assert len(rows) == 3
    isins = {row[0] for row in rows}
    assert isins == {"IE00B4L5Y983", "IE00BK5BQT80", "IE00BKM4GZ66"}


def test_seed_is_idempotent_on_repeated_run(engine: Engine) -> None:
    seed(yaml_path=FIXTURE)
    seed(yaml_path=FIXTURE)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM etfs")).scalar_one()
    assert count == 3


def test_seed_advances_updated_at_but_preserves_created_at(engine: Engine) -> None:
    seed(yaml_path=FIXTURE)
    with engine.connect() as conn:
        created_a, updated_a = conn.execute(
            text("SELECT created_at, updated_at FROM etfs WHERE isin = 'IE00B4L5Y983'")
        ).one()
    assert isinstance(created_a, datetime)
    assert isinstance(updated_a, datetime)

    seed(yaml_path=FIXTURE)
    with engine.connect() as conn:
        created_b, updated_b = conn.execute(
            text("SELECT created_at, updated_at FROM etfs WHERE isin = 'IE00B4L5Y983'")
        ).one()
    assert created_a == created_b
    assert updated_b >= updated_a


def test_seed_sets_last_ingested_at(engine: Engine) -> None:
    seed(yaml_path=FIXTURE)
    with engine.connect() as conn:
        last_ingested = conn.execute(
            text("SELECT last_ingested_at FROM etfs WHERE isin = 'IE00B4L5Y983'")
        ).scalar_one()
    assert isinstance(last_ingested, datetime)
