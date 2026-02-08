"""Dashboard response schemas."""

from pydantic import BaseModel


class AccountSummary(BaseModel):
    """Single account in the dashboard summary."""

    id: int
    name: str
    type: str | None = None
    institution: str | None = None
    currency: str | None = None
    value_usd: float
    value_ils: float
    value: float | None = None
    display_currency: str = "USD"


class AllocationEntry(BaseModel):
    """Asset-class allocation row."""

    asset_class: str
    total_value: float
    holding_count: int
    display_currency: str = "USD"


class TopHoldingEntry(BaseModel):
    """Single holding in the top-holdings list."""

    id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    account_name: str
    quantity: float
    cost_basis: float
    current_price: float | None = None
    currency: str = "USD"
    market_value: float


class PerformanceEntry(BaseModel):
    """Historical performance data point."""

    date: str
    value_usd: float
    value_ils: float
    value: float | None = None
    currency: str | None = None


class DashboardSummaryResponse(BaseModel):
    """Full dashboard summary response."""

    total_value: float
    display_currency: str = "USD"
    total_value_usd: float
    total_value_ils: float
    day_change: float | None = None
    day_change_pct: float | None = None
    previous_close_value: float | None = None
    accounts: list[AccountSummary]
    asset_allocation: list[AllocationEntry]
    top_holdings: list[TopHoldingEntry]
    historical_performance: list[PerformanceEntry]
