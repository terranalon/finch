"""Exchange Rate model - represents currency exchange rates."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ExchangeRate(Base):
    """Exchange Rate model for storing historical currency exchange rates."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "date", name="uq_exchange_rate"),
        Index("idx_rates_currencies_date", "from_currency", "to_currency", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<ExchangeRate({self.from_currency}/{self.to_currency}={self.rate} on {self.date})>"
