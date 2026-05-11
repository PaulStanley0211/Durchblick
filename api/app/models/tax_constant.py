from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TaxConstant(Base):
    __tablename__ = "tax_constants"

    year: Mapped[int] = mapped_column(primary_key=True)
    basiszins: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    sparerpauschbetrag_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    teilfreistellung_equity: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    teilfreistellung_mixed: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    capital_gains_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    solidaritaetszuschlag_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
