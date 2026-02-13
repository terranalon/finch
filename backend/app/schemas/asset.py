"""Pydantic schemas for Asset model."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    """Base Asset schema with common fields."""

    symbol: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    asset_class: str = Field(
        ...,
        description="Asset class: Stock, Bond, ETF, MutualFund, Crypto, Cash, RealEstate, Commodity, PrivateEquity, Art, Other",
    )
    category: str | None = Field(
        None, max_length=100, description="Sector for stocks, Category for ETFs"
    )
    industry: str | None = Field(None, max_length=100)
    currency: str = Field(default="USD", max_length=3, description="Asset currency (ISO code)")
    is_manual_valuation: bool = False
    data_source: str | None = Field(
        None, max_length=50, description="Data source: YahooFinance, AlphaVantage, Manual, etc."
    )
    meta_data: dict[str, Any] | None = None


class AssetCreate(AssetBase):
    """Schema for creating a new Asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an existing Asset."""

    symbol: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=200)
    asset_class: str | None = None
    category: str | None = Field(None, max_length=100)
    industry: str | None = Field(None, max_length=100)
    currency: str | None = Field(None, max_length=3)
    is_manual_valuation: bool | None = None
    is_favorite: bool | None = None
    data_source: str | None = Field(None, max_length=50)
    last_fetched_price: Decimal | None = None
    meta_data: dict[str, Any] | None = None


class Asset(AssetBase):
    """Schema for Asset responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_favorite: bool = False
    last_fetched_price: Decimal | None = None
    last_fetched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetMarketResponse(BaseModel):
    """Asset with price change data for market view."""

    id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    category: str | None = None
    industry: str | None = None
    currency: str | None = None
    is_favorite: bool = False
    last_fetched_price: float | None = None
    last_fetched_at: str | None = None
    data_source: str | None = None
    change_1d: float | None = None
    change_1d_pct: float | None = None
    change_1w: float | None = None
    change_1w_pct: float | None = None
    change_1m: float | None = None
    change_1m_pct: float | None = None
