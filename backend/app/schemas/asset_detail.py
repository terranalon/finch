"""Pydantic schemas for the asset detail endpoint."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyMetricsResponse(BaseModel):
    """Latest daily metrics for an asset (OHLCV + fundamentals)."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    # OHLCV
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None
    # Fundamentals
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    forward_pe: Decimal | None = None
    eps: Decimal | None = None
    dividend_rate: Decimal | None = None
    dividend_yield: Decimal | None = None
    payout_ratio: Decimal | None = None
    # Crypto
    circulating_supply: Decimal | None = None
    market_cap_rank: int | None = None
    dominance: Decimal | None = None


class AssetDetailResponse(BaseModel):
    """Full asset detail response combining asset info + latest daily metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str
    asset_class: str
    currency: str
    is_favorite: bool = False
    category: str | None = None
    industry: str | None = None
    last_fetched_price: Decimal | None = None
    last_fetched_at: datetime | None = None

    # About
    description: str | None = None
    exchange: str | None = None
    website: str | None = None
    ceo: str | None = None
    employees: int | None = None

    # Slow-changing stats
    beta: Decimal | None = None
    avg_volume: int | None = None
    earnings_date: date | None = None
    ex_dividend_date: date | None = None
    target_est: Decimal | None = None
    week_52_high: Decimal | None = None
    week_52_low: Decimal | None = None
    peg_ratio: Decimal | None = None

    # ETF-specific
    expense_ratio: Decimal | None = None
    fund_family: str | None = None
    nav: Decimal | None = None

    # Crypto
    max_supply: Decimal | None = None
    ath: Decimal | None = None
    ath_date: date | None = None
    atl: Decimal | None = None
    atl_date: date | None = None

    created_at: datetime
    updated_at: datetime

    daily_metrics: DailyMetricsResponse | None = None
