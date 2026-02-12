"""Price response schemas."""

from typing import Any

from pydantic import BaseModel


class PriceUpdateResponse(BaseModel):
    """Response for POST /api/prices/update."""

    status: str
    message: str
    asset_class: str | None = None
    stats: dict[str, Any] | None = None


class SingleAssetPriceResponse(BaseModel):
    """Response for POST /api/prices/update/{asset_id}."""

    status: str
    message: str
    asset_id: int
    symbol: str
    price: float | None = None
    updated_at: str | None = None


class HistoricalPricePoint(BaseModel):
    """Single data point in historical price series."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class HistoricalPriceResponse(BaseModel):
    """Response for GET /api/prices/historical/{symbol}."""

    symbol: str
    period: str
    currency: str | None = None
    data: list[HistoricalPricePoint]
