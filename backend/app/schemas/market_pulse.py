"""Market pulse response schemas."""

from pydantic import BaseModel


class MarketPulseItemResponse(BaseModel):
    """Single market index/asset in the pulse card."""

    symbol: str
    name: str
    price: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    sparkline: list[float]


class MarketPulseResponse(BaseModel):
    """Response for GET /api/dashboard/market-pulse."""

    items: list[MarketPulseItemResponse]
