"""Transaction model - represents historical trades and updates."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Transaction(Base):
    """Transaction model representing historical record of all trades and updates."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_holding", "holding_id"),
        Index("idx_transactions_date", "date"),
        Index("idx_transactions_type_date", "type", "date"),  # For faster dividend queries
        Index("idx_transactions_broker_source", "broker_source_id"),  # For source tracking
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    holding_id: Mapped[int] = mapped_column(ForeignKey("holdings.id", ondelete="CASCADE"))
    broker_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_data_sources.id", ondelete="SET NULL")
    )  # Which import provided this transaction
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(50))  # 'Buy', 'Sell', 'Dividend', etc.
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))  # None for dividends
    price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))  # None for dividends
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # For cash dividends
    fees: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    currency_rate_to_usd_at_date: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Forex-specific fields (only populated for Forex Conversion transactions)
    to_holding_id: Mapped[int | None] = mapped_column(
        ForeignKey("holdings.id", ondelete="SET NULL"), nullable=True
    )  # The destination currency holding for forex conversions
    to_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Amount received in forex
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))  # Forex exchange rate

    # Relationships
    holding: Mapped["Holding"] = relationship(
        back_populates="transactions", foreign_keys=[holding_id]
    )
    to_holding: Mapped["Holding | None"] = relationship(foreign_keys=[to_holding_id])
    broker_source: Mapped["BrokerDataSource | None"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type='{self.type}', date={self.date}, quantity={self.quantity})>"
