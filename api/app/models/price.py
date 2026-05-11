from datetime import date as date_t
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("isin", "date", name="uq_prices_isin_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(String(12), ForeignKey("etfs.isin"), index=True)
    date: Mapped[date_t] = mapped_column(Date)
    nav: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    currency: Mapped[str] = mapped_column(CHAR(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
