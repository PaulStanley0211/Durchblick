from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etf


def list_etfs(session: Session) -> list[Etf]:
    """Return all ETFs ordered by name."""
    return list(session.execute(select(Etf).order_by(Etf.name)).scalars())


def get_etf(session: Session, isin: str) -> Etf | None:
    """Return the ETF with the given ISIN, or None if absent."""
    return session.get(Etf, isin)
