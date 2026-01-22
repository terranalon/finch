"""Asset price history model."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AssetPrice(Base):
    """Historical price data for assets (end-of-day closing prices only)."""

    __tablename__ = "asset_prices"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_price_date"),
        Index("idx_asset_prices_asset_date", "asset_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    closing_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), comment="End-of-day closing price"
    )
    currency: Mapped[str] = mapped_column(String(3))
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"<AssetPrice(asset_id={self.asset_id}, date={self.date}, closing_price={self.closing_price})>"
