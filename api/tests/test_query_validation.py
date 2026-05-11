"""Endpoint query-validation tests that do not require a DB.

FastAPI rejects malformed query parameters before any handler runs,
so these tests can live outside the integration-test directory and
skip the DB-seed autouse fixture.
"""

from httpx import AsyncClient


async def test_comparison_rejects_short_isin(client: AsyncClient) -> None:
    response = await client.get("/comparison", params={"isin_a": "IE00", "isin_b": "IE00BK5BQT80"})
    assert response.status_code == 422
