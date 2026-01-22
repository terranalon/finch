"""Historical Snapshot model - represents daily portfolio value snapshots."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class HistoricalSnapshot(Base):
    """Historical Snapshot model for daily portfolio value tracking."""

    __tablename__ = "historical_snapshots"
    __table_args__ = (
        UniqueConstraint("date", "account_id", name="uq_snapshot_date_account"),
        Index("idx_snapshots_date", "date"),
        Index("idx_snapshots_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    total_value_usd: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_value_ils: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="historical_snapshots")

    def __repr__(self) -> str:
        return f"<HistoricalSnapshot(date={self.date}, account_id={self.account_id}, usd={self.total_value_usd})>"
