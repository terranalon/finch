"""Pydantic schemas for market data refresh endpoints."""

from datetime import date

from pydantic import BaseModel, Field


class RefreshStats(BaseModel):
    """Base statistics for refresh operations."""

    date: date
    updated: int = Field(..., description="Number of records inserted/updated")
    skipped: int = Field(..., description="Number of records skipped (already exist)")
    failed: int = Field(0, description="Number of failed fetches")


class ExchangeRateRefreshResponse(RefreshStats):
    """Response for exchange rate refresh endpoint."""

    pairs: list[str] = Field(default_factory=list, description="Currency pairs updated")


class PriceRefreshError(BaseModel):
    """Details about a failed price fetch."""

    symbol: str = Field(..., description="Ticker symbol that failed")
    error: str = Field(..., description="Error message from the fetch attempt")


class PriceRefreshResponse(RefreshStats):
    """Response for stock/crypto price refresh endpoints."""

    source: str = Field(..., description="Data source used (yfinance, coingecko, cryptocompare)")
    errors: list[PriceRefreshError] = Field(default_factory=list)
