from httpx import AsyncClient

MSCI_WORLD = "IE00B4L5Y983"
FTSE_ALL_WORLD = "IE00BK5BQT80"
UNKNOWN_ISIN = "XX0000000000"


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


async def test_list_etfs_returns_all_mock_entries(client: AsyncClient) -> None:
    response = await client.get("/etfs")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 3
    isins = {row["isin"] for row in body}
    assert isins == {MSCI_WORLD, FTSE_ALL_WORLD, "IE00BKM4GZ66"}
