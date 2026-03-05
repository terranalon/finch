"""Value objects for portfolio services.

Plain dataclasses for service-layer return types. Routers convert these
to Pydantic schemas at the API boundary (Clean Architecture dependency rule).
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class HoldingValue:
    """Result of valuing a single holding."""

    asset_id: int
    ticker: str
    name: str | None
    asset_class: str | None
    currency: str
    quantity: Decimal
    market_value_usd: Decimal
    is_cash: bool

    # Defaults for callers that don't track cost basis or native value
    cost_basis_native: Decimal = Decimal("0")
    market_value_native: Decimal = Decimal("0")


@dataclass
class AccountValue:
    """Aggregated value for a single brokerage account."""

    account_id: int
    name: str
    account_type: str | None
    institution: str | None
    currency: str | None
    value_usd: Decimal
    value_ils: Decimal


@dataclass
class AccountHolding:
    """Per-account breakdown within a position."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None
    institution: str | None
    quantity: Decimal
    cost_basis_native: Decimal
    market_value_native: Decimal | None
    pnl_native: Decimal | None
    cost_basis_usd: Decimal
    market_value_usd: Decimal | None
    pnl_usd: Decimal | None
    pnl_pct: Decimal | None
    strategy_horizon: str | None


@dataclass
class PositionResult:
    """Aggregated position for one asset across all accounts."""

    asset_id: int
    symbol: str
    name: str | None
    asset_class: str | None
    category: str | None
    industry: str | None
    currency: str
    is_favorite: bool

    current_price: Decimal | None
    previous_close_price: Decimal | None
    day_change: Decimal | None
    day_change_pct: Decimal | None
    day_change_date: str | None
    is_market_closed: bool

    total_quantity: Decimal
    total_cost_basis_native: Decimal
    total_market_value_native: Decimal | None
    total_pnl_native: Decimal | None
    avg_cost_per_unit_native: Decimal

    total_cost_basis_usd: Decimal
    total_market_value_usd: Decimal | None
    total_pnl_usd: Decimal | None
    total_pnl_pct: Decimal | None
    avg_cost_per_unit_usd: Decimal

    accounts: list[AccountHolding] = field(default_factory=list)

    @property
    def account_count(self) -> int:
        return len(self.accounts)


@dataclass
class AllocationItem:
    """Single asset class allocation entry."""

    asset_class: str
    total_value: Decimal
    holding_count: int


@dataclass
class TopHolding:
    """A single top-holding entry for the dashboard."""

    holding_id: int
    symbol: str
    name: str | None
    asset_class: str | None
    account_name: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Decimal | None
    currency: str
    market_value_usd: Decimal
    day_change_pct: Decimal | None = None


@dataclass
class PerformancePoint:
    """Single historical performance data point."""

    date: str
    value_usd: float
    value_ils: float


@dataclass
class DashboardSummary:
    """Complete dashboard summary result."""

    total_value_usd: Decimal
    total_value_ils: Decimal
    day_change_usd: Decimal | None
    day_change_pct: Decimal | None
    previous_close_value_usd: Decimal | None
    accounts: list[AccountValue]
    asset_allocation: list[AllocationItem]
    top_holdings: list[TopHolding]
    historical_performance: list[PerformancePoint]
    total_cost_basis_usd: Decimal = Decimal("0")
    total_cash_usd: Decimal = Decimal("0")
