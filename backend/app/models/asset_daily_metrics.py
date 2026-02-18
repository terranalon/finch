"""Asset daily metrics model -- OHLCV and fundamental data."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AssetDailyMetrics(Base):
    """Daily market metrics for assets (OHLCV + fundamentals).

    One row per asset per date. Today's row is upserted intraday;
    past rows are immutable end-of-day snapshots.
    """

    __tablename__ = "asset_daily_metrics"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_daily_metrics_asset_date"),
        Index("idx_asset_daily_metrics_asset_date", "asset_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)

    # OHLCV
    open: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    low: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    close: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)

    # Daily-changing fundamentals
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    forward_pe: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    dividend_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    payout_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    # Crypto daily
    circulating_supply: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    market_cap_rank: Mapped[int | None] = mapped_column(Integer)
    dominance: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    # Meta
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="daily_metrics")

    def __repr__(self) -> str:
        return f"<AssetDailyMetrics(asset_id={self.asset_id}, date={self.date})>"
