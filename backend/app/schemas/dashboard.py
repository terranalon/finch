"""Dashboard response schemas."""

from pydantic import BaseModel


class DashboardAccountResponse(BaseModel):
    """Single account in dashboard summary."""

    id: int
    name: str
    type: str | None = None
    institution: str | None = None
    currency: str | None = None
    value: float
    value_usd: float
    value_ils: float
    display_currency: str


class AssetAllocationResponse(BaseModel):
    """Asset class allocation entry."""

    asset_class: str
    total_value: float
    holding_count: int
    display_currency: str


class TopHoldingResponse(BaseModel):
    """Top holding entry in dashboard."""

    id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    account_name: str
    quantity: float
    cost_basis: float
    current_price: float | None = None
    currency: str
    market_value: float


class HistoricalPerformancePoint(BaseModel):
    """Single point in historical performance series."""

    date: str
    value: float | None = None
    value_usd: float | None = None
    value_ils: float | None = None
    currency: str | None = None


class DashboardSummaryResponse(BaseModel):
    """Response for GET /api/dashboard/summary."""

    total_value: float
    display_currency: str
    total_value_usd: float
    total_value_ils: float
    day_change: float | None = None
    day_change_pct: float | None = None
    previous_close_value: float | None = None
    accounts: list[DashboardAccountResponse]
    asset_allocation: list[AssetAllocationResponse]
    top_holdings: list[TopHoldingResponse]
    historical_performance: list[HistoricalPerformancePoint]


class BenchmarkDataPoint(BaseModel):
    """Single data point in benchmark performance series."""

    date: str
    price: float
    performance: float


class BenchmarkResponse(BaseModel):
    """Response for GET /api/dashboard/benchmark."""

    symbol: str
    name: str
    data: list[BenchmarkDataPoint]
    error: str | None = None
