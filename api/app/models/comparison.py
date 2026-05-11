from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Comparison(Base):
    """Anonymous log of ETF pairs compared.

    Per PLAN.md section 7: no IP, no user agent, no fingerprint.
    """

    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    isin_a: Mapped[str] = mapped_column(String(12), ForeignKey("etfs.isin"), index=True)
    isin_b: Mapped[str] = mapped_column(String(12), ForeignKey("etfs.isin"), index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
