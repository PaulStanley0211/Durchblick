from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Etf(Base):
    __tablename__ = "etfs"

    isin: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str] = mapped_column(String(255))
    ter: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    replication_method: Mapped[str | None] = mapped_column(String(50))
    distribution_policy: Mapped[str | None] = mapped_column(String(20))
    domicile: Mapped[str | None] = mapped_column(CHAR(2))
    aum_eur: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    inception_date: Mapped[date | None] = mapped_column(Date)
    index_tracked: Mapped[str | None] = mapped_column(String(255))
    teilfreistellung_class: Mapped[str | None] = mapped_column(String(20))
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # ORM-only; seed_etfs.py sets this explicitly on upsert
    )
