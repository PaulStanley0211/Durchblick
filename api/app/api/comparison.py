"""ETF list and comparison endpoints, backed by the etfs table.

The /etfs endpoint returns the seeded ETF universe ordered by name.
The /comparison endpoint returns the two requested ETFs plus a
placeholder after-tax outcome. Phase 8 replaces the hardcoded
after-tax map with a real tax-module call; Phase 9 introduces a
prices-aware comparison.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Etf
from app.repositories import etfs as etfs_repo

router = APIRouter()

# Phase 9 replaces this with a tax-module call against price-feed data.
_HARDCODED_AFTER_TAX_EUR: dict[str, float] = {
    "IE00B4L5Y983": 14823.45,
    "IE00BK5BQT80": 14752.10,
    "IE00BKM4GZ66": 13218.70,
}
_DEFAULT_INVESTMENT_EUR = 10000
_DEFAULT_HORIZON_YEARS = 10
_DEFAULT_AFTER_TAX_EUR = 14000.00


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


def _to_response(etf: Etf) -> EtfResponse:
    # Phase 7 seeds always populate every field. A null here indicates
    # a corrupted row that must not be silently coerced to defaults.
    if (
        etf.ter is None
        or etf.replication_method is None
        or etf.distribution_policy is None
        or etf.domicile is None
        or etf.aum_eur is None
        or etf.inception_date is None
        or etf.index_tracked is None
        or etf.teilfreistellung_class is None
    ):
        raise HTTPException(status_code=500, detail=f"ETF {etf.isin} has null fields")
    return EtfResponse(
        isin=etf.isin,
        name=etf.name,
        issuer=etf.issuer,
        ter=float(etf.ter),
        replication_method=etf.replication_method,
        distribution_policy=etf.distribution_policy,
        domicile=etf.domicile,
        aum_eur=float(etf.aum_eur),
        inception_date=etf.inception_date,
        index_tracked=etf.index_tracked,
        teilfreistellung_class=etf.teilfreistellung_class,
    )


@router.get("/etfs", response_model=list[EtfResponse])
def list_etfs(session: Annotated[Session, Depends(get_session)]) -> list[EtfResponse]:
    return [_to_response(etf) for etf in etfs_repo.list_etfs(session)]


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(
    isin_a: Annotated[str, Query(min_length=12, max_length=12)],
    isin_b: Annotated[str, Query(min_length=12, max_length=12)],
    session: Annotated[Session, Depends(get_session)],
) -> ComparisonResponse:
    etf_a = etfs_repo.get_etf(session, isin_a)
    if etf_a is None:
        raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin_a}")
    etf_b = etfs_repo.get_etf(session, isin_b)
    if etf_b is None:
        raise HTTPException(status_code=404, detail=f"Unknown ISIN: {isin_b}")
    return ComparisonResponse(
        horizon_years=_DEFAULT_HORIZON_YEARS,
        investment_eur=_DEFAULT_INVESTMENT_EUR,
        etfs=[_to_response(etf_a), _to_response(etf_b)],
        after_tax_eur=[
            AfterTaxOutcome(
                isin=isin_a,
                value_eur=_HARDCODED_AFTER_TAX_EUR.get(isin_a, _DEFAULT_AFTER_TAX_EUR),
            ),
            AfterTaxOutcome(
                isin=isin_b,
                value_eur=_HARDCODED_AFTER_TAX_EUR.get(isin_b, _DEFAULT_AFTER_TAX_EUR),
            ),
        ],
    )
