"""Integration test: /etfs and /comparison against a seeded Postgres.

Seeds the 3-row fixture, then exercises the two endpoints. The
fixture is the same one used by test_seed_etfs_db.py, so the three
expected ISINs are MSCI World, FTSE All-World, and EM IMI.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from scripts.seed_etfs import seed

MSCI_WORLD = "IE00B4L5Y983"
FTSE_ALL_WORLD = "IE00BK5BQT80"
EM_IMI = "IE00BKM4GZ66"
UNKNOWN_ISIN = "XX0000000000"

FIXTURE = Path(__file__).parent.parent / "fixtures" / "etfs_seed_sample.yaml"


@pytest.fixture(scope="module")
def engine() -> Engine:
    return create_engine(get_settings().database_url)


@pytest.fixture(autouse=True)
def _seed_three_etfs(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE prices, etfs RESTART IDENTITY CASCADE"))
    seed(yaml_path=FIXTURE)


async def test_list_etfs_returns_three_rows_ordered_by_name(client: AsyncClient) -> None:
    response = await client.get("/etfs")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 3
    # Names alphabetically (case-insensitive, matching Postgres ORDER BY name):
    # iShares Core MSCI EM IMI..., iShares Core MSCI World..., Vanguard FTSE...
    names = [row["name"] for row in body]
    assert names == sorted(names, key=str.lower)
    isins = {row["isin"] for row in body}
    assert isins == {MSCI_WORLD, FTSE_ALL_WORLD, EM_IMI}


async def test_list_etfs_row_shape_matches_phase6_contract(client: AsyncClient) -> None:
    response = await client.get("/etfs")
    body = response.json()
    expected_keys = {
        "isin",
        "name",
        "issuer",
        "ter",
        "replication_method",
        "distribution_policy",
        "domicile",
        "aum_eur",
        "inception_date",
        "index_tracked",
        "teilfreistellung_class",
    }
    for row in body:
        assert set(row.keys()) == expected_keys


async def test_comparison_happy_path(client: AsyncClient) -> None:
    response = await client.get(
        "/comparison", params={"isin_a": MSCI_WORLD, "isin_b": FTSE_ALL_WORLD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["horizon_years"] == 10
    assert body["investment_eur"] == 10000
    assert len(body["etfs"]) == 2
    assert body["etfs"][0]["isin"] == MSCI_WORLD
    assert body["etfs"][1]["isin"] == FTSE_ALL_WORLD
    assert body["etfs"][0]["name"] == "iShares Core MSCI World UCITS ETF"
    assert len(body["after_tax_eur"]) == 2
    assert body["after_tax_eur"][0]["isin"] == MSCI_WORLD
    assert body["after_tax_eur"][0]["value_eur"] > 0


async def test_comparison_unknown_isin_a_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/comparison", params={"isin_a": UNKNOWN_ISIN, "isin_b": FTSE_ALL_WORLD}
    )
    assert response.status_code == 404
    assert UNKNOWN_ISIN in response.json()["detail"]


async def test_comparison_unknown_isin_b_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/comparison", params={"isin_a": MSCI_WORLD, "isin_b": UNKNOWN_ISIN}
    )
    assert response.status_code == 404
    assert UNKNOWN_ISIN in response.json()["detail"]


async def test_comparison_rejects_short_isin(client: AsyncClient) -> None:
    response = await client.get("/comparison", params={"isin_a": "IE00", "isin_b": FTSE_ALL_WORLD})
    assert response.status_code == 422
