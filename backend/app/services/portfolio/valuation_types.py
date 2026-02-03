"""Value objects for portfolio valuation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class DayChangeResult:
    """Day change calculation result."""

    day_change: Decimal | None
    day_change_pct: Decimal | None
    previous_close_price: Decimal | None
    day_change_date: str | None
    is_market_closed: bool
