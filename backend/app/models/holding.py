"""Holding model - represents current positions in accounts."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Holding(Base):
    """Holding model representing current positions in accounts (aggregate view)."""

    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("account_id", "asset_id", name="uq_holding_account_asset"),
        Index("idx_holdings_account", "account_id"),
        Index("idx_holdings_asset", "asset_id"),
        Index("idx_holdings_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    strategy_horizon: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="holdings")
    asset: Mapped["Asset"] = relationship(back_populates="holdings")
    holding_lots: Mapped[list["HoldingLot"]] = relationship(
        back_populates="holding", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="holding",
        cascade="all, delete-orphan",
        foreign_keys="Transaction.holding_id",
    )

    def __repr__(self) -> str:
        return f"<Holding(id={self.id}, account_id={self.account_id}, asset_id={self.asset_id}, quantity={self.quantity})>"
