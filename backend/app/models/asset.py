"""Asset model - represents investment assets."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Asset(Base):
    """Asset model representing investment assets (stocks, crypto, real estate, etc.)."""

    __tablename__ = "assets"
    __table_args__ = (
        Index("idx_assets_symbol", "symbol"),
        Index("idx_assets_class", "asset_class"),
        Index("idx_assets_cusip", "cusip"),
        Index("idx_assets_isin", "isin"),
        Index("idx_assets_conid", "conid"),
        Index("idx_assets_tase_security_number", "tase_security_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_class: Mapped[str] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(
        String(100)
    )  # Sector for stocks, Category for ETFs
    industry: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Permanent identifiers (don't change with ticker symbol changes)
    cusip: Mapped[str | None] = mapped_column(String(20))
    isin: Mapped[str | None] = mapped_column(String(20))
    conid: Mapped[str | None] = mapped_column(String(50))  # IBKR contract ID
    figi: Mapped[str | None] = mapped_column(String(20))  # Bloomberg Global ID
    tase_security_number: Mapped[str | None] = mapped_column(String(20))  # Israeli מספר נייר ערך
    is_manual_valuation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str | None] = mapped_column(String(50))
    last_fetched_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    last_fetched_at: Mapped[datetime | None]
    meta_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    price_history: Mapped[list["AssetPrice"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, symbol='{self.symbol}', name='{self.name}')>"
