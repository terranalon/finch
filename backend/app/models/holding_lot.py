"""Holding Lot model - represents individual purchase lots for FIFO tracking."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class HoldingLot(Base):
    """Holding Lot model for FIFO cost basis tracking."""

    __tablename__ = "holding_lots"
    __table_args__ = (
        Index("idx_lots_holding", "holding_id"),
        Index("idx_lots_purchase_date", "purchase_date"),
        Index("idx_lots_closed", "is_closed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    holding_id: Mapped[int] = mapped_column(ForeignKey("holdings.id", ondelete="CASCADE"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(15, 4))
    purchase_date: Mapped[date] = mapped_column(Date)
    purchase_price_original: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    fees: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    remaining_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    holding: Mapped["Holding"] = relationship(back_populates="holding_lots")

    def __repr__(self) -> str:
        return f"<HoldingLot(id={self.id}, holding_id={self.holding_id}, quantity={self.quantity}, date={self.purchase_date})>"
