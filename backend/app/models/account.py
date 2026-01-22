"""Account model - represents financial accounts."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.broker_data_source import BrokerDataSource
    from app.models.historical_snapshot import HistoricalSnapshot
    from app.models.holding import Holding
    from app.models.portfolio import Portfolio


class Account(Base):
    """Account model representing financial accounts belonging to portfolios."""

    __tablename__ = "accounts"
    __table_args__ = (Index("idx_accounts_portfolio", "portfolio_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    institution: Mapped[str | None] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3))
    account_number: Mapped[str | None] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    broker_type: Mapped[str | None] = mapped_column(String(50))  # 'ibkr', 'binance', 'ibi', etc.
    meta_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="accounts")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    historical_snapshots: Mapped[list["HistoricalSnapshot"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    broker_data_sources: Mapped[list["BrokerDataSource"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"
