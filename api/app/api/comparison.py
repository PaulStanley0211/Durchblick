"""Phase 6 comparison endpoint.

Returns mock side-by-side ETF data and a hardcoded after-tax outcome
for any two ISINs in /shared/mock_etfs.json. Phase 9 replaces the
hardcoded numbers with real DB lookups and the Phase 8 tax module.
The response shape established here is the contract front and back
end will keep through Phase 9.
"""

import json
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

_MOCK_PATH = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "mock_etfs.json"

_HARDCODED_AFTER_TAX_EUR: dict[str, float] = {
    "IE00B4L5Y983": 14823.45,
    "IE00BK5BQT80": 14752.10,
    "IE00BKM4GZ66": 13218.70,
}

_DEFAULT_INVESTMENT_EUR = 10000
_DEFAULT_HORIZON_YEARS = 10


class EtfResponse(BaseModel):
    isin: str
    name: str
    issuer: str
    ter: float
    replication_method: str
    distribution_policy: str
    domicile: str
    aum_eur: float
    inception_date: date
    index_tracked: str
    teilfreistellung_class: str


class AfterTaxOutcome(BaseModel):
    isin: str
    value_eur: float


class ComparisonResponse(BaseModel):
    horizon_years: int
    investment_eur: int
    etfs: list[EtfResponse]
    after_tax_eur: list[AfterTaxOutcome]


def _load_mock_etfs() -> dict[str, EtfResponse]:
    with _MOCK_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {row["isin"]: EtfResponse.model_validate(row) for row in data["etfs"]}


@router.get("/etfs", response_model=list[EtfResponse])
def list_etfs() -> list[EtfResponse]:
    return list(_load_mock_etfs().values())


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(
    isin_a: Annotated[str, Query(min_length=12, max_length=12)],
    isin_b: Annotated[str, Query(min_length=12, max_length=12)],
) -> ComparisonResponse:
    etfs = _load_mock_etfs()
    if isin_a not in etfs:
        raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin_a}")
    if isin_b not in etfs:
        raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin_b}")
    return ComparisonResponse(
        horizon_years=_DEFAULT_HORIZON_YEARS,
        investment_eur=_DEFAULT_INVESTMENT_EUR,
        etfs=[etfs[isin_a], etfs[isin_b]],
        after_tax_eur=[
            AfterTaxOutcome(
                isin=isin_a,
                value_eur=_HARDCODED_AFTER_TAX_EUR.get(isin_a, 14000.00),
            ),
            AfterTaxOutcome(
                isin=isin_b,
                value_eur=_HARDCODED_AFTER_TAX_EUR.get(isin_b, 14000.00),
            ),
        ],
    )
