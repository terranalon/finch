"""Position response schemas."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

# Decimal that serializes as float in JSON responses (preserves numeric wire format)
JsonDecimal = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class PositionAccountDetail(BaseModel):
    """Account-level breakdown within a position."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None = None
    institution: str | None = None
    quantity: JsonDecimal
    cost_basis_native: JsonDecimal = Field(..., description="Cost basis in asset's native currency")
    market_value_native: JsonDecimal | None = Field(
        None, description="Market value in native currency"
    )
    pnl_native: JsonDecimal | None = Field(None, description="P&L in native currency")
    cost_basis: JsonDecimal = Field(..., description="Cost basis in display currency")
    market_value: JsonDecimal | None = Field(None, description="Market value in display currency")
    pnl: JsonDecimal | None = Field(None, description="P&L in display currency")
    pnl_pct: JsonDecimal | None = Field(None, description="P&L percentage")
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
    current_price: JsonDecimal | None = None
    current_price_display: JsonDecimal | None = Field(
        None, description="Current price in display currency"
    )
    previous_close_price: JsonDecimal | None = None
    day_change: JsonDecimal | None = None
    day_change_pct: JsonDecimal | None = None
    day_change_date: str | None = None
    is_market_closed: bool = False

    # Aggregated values (native currency)
    total_quantity: JsonDecimal
    total_cost_basis_native: JsonDecimal
    total_market_value_native: JsonDecimal | None = None
    total_pnl_native: JsonDecimal | None = None
    avg_cost_per_unit_native: JsonDecimal = Decimal("0")

    # Aggregated values (display currency)
    total_cost_basis: JsonDecimal
    total_market_value: JsonDecimal | None = None
    current_value: JsonDecimal | None = Field(None, description="Alias for total_market_value")
    total_pnl: JsonDecimal | None = None
    total_pnl_pct: JsonDecimal | None = None
    avg_cost_per_unit: JsonDecimal = Decimal("0")

    display_currency: str = "USD"
    account_count: int = 0
    accounts: list[PositionAccountDetail] = []
