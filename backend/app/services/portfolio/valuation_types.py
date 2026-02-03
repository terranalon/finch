"""Value objects for portfolio valuation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class HoldingValue:
    """Calculated values for a single holding."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None
    institution: str | None
    quantity: Decimal

    # Native currency values
    cost_basis_native: Decimal
    market_value_native: Decimal | None
    pnl_native: Decimal | None
    pnl_pct: Decimal | None

    # Display currency values
    cost_basis: Decimal
    market_value: Decimal | None
    pnl: Decimal | None

    strategy_horizon: str | None = None


@dataclass
class DayChangeResult:
    """Day change calculation result."""

    day_change: Decimal | None
    day_change_pct: Decimal | None
    previous_close_price: Decimal | None
    day_change_date: str | None
    is_market_closed: bool


@dataclass
class PositionSummary:
    """Aggregated position across accounts."""

    asset_id: int
    symbol: str
    name: str | None
    asset_class: str | None
    category: str | None
    industry: str | None
    currency: str
    is_favorite: bool
    current_price: Decimal | None

    # Totals in native currency
    total_quantity: Decimal
    total_cost_basis_native: Decimal
    total_market_value_native: Decimal | None
    total_pnl_native: Decimal | None

    # Totals in display currency
    total_cost_basis: Decimal
    total_market_value: Decimal | None
    total_pnl: Decimal | None
    total_pnl_pct: Decimal | None

    # Day change
    day_change: DayChangeResult | None

    # Account breakdown
    holdings: list[HoldingValue]
    account_count: int
