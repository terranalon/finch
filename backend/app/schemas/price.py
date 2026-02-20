"""Price response schemas."""

from typing import Any

from pydantic import BaseModel

from app.schemas.common import StatusResponse


class PriceUpdateResponse(StatusResponse):
    """Response for POST /api/prices."""

    asset_class: str | None = None
    stats: dict[str, Any] | None = None


class SingleAssetPriceResponse(StatusResponse):
    """Response for PATCH /api/assets/{asset_id}/price."""

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
    dividend_dates: list[str] = []
