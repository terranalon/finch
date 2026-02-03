"""Position response schemas."""

from pydantic import BaseModel, Field


class PositionAccountDetail(BaseModel):
    """Account-level breakdown within a position."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None = None
    institution: str | None = None
    quantity: float
    cost_basis_native: float = Field(..., description="Cost basis in asset's native currency")
    market_value_native: float | None = Field(None, description="Market value in native currency")
    pnl_native: float | None = Field(None, description="P&L in native currency")
    cost_basis: float = Field(..., description="Cost basis in display currency")
    market_value: float | None = Field(None, description="Market value in display currency")
    pnl: float | None = Field(None, description="P&L in display currency")
    pnl_pct: float | None = Field(None, description="P&L percentage")
    strategy_horizon: str | None = None


class PositionResponse(BaseModel):
    """Aggregated position for an asset across accounts."""

    asset_id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    category: str | None = None
    industry: str | None = None
    currency: str = "USD"
    is_favorite: bool = False

    # Price data
    current_price: float | None = None
    current_price_display: float | None = Field(
        None, description="Current price in display currency"
    )
    previous_close_price: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    day_change_date: str | None = None
    is_market_closed: bool = False

    # Aggregated values (native currency)
    total_quantity: float
    total_cost_basis_native: float
    total_market_value_native: float | None = None
    total_pnl_native: float | None = None
    avg_cost_per_unit_native: float = 0

    # Aggregated values (display currency)
    total_cost_basis: float
    total_market_value: float | None = None
    current_value: float | None = Field(None, description="Alias for total_market_value")
    total_pnl: float | None = None
    total_pnl_pct: float | None = None
    avg_cost_per_unit: float = 0

    display_currency: str = "USD"
    account_count: int = 0
    accounts: list[PositionAccountDetail] = []
