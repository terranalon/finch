"""Portfolio valuation service - single source of truth for value calculations.

This service centralizes all valuation logic that was previously
duplicated across positions.py and dashboard.py (~200 lines).
"""

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import Account, Asset, Holding
from app.services.portfolio.valuation_types import (
    DayChangeResult,
    HoldingValue,
)
from app.services.shared.currency_service import CurrencyService

if TYPE_CHECKING:
    from app.services.repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)


class PortfolioValuationService:
    """Calculates portfolio values, P&L, and day changes.

    This service centralizes all valuation logic that was previously
    duplicated across positions.py and dashboard.py.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._price_repo: PriceRepository | None = None

    @property
    def price_repo(self) -> "PriceRepository":
        """Lazy-load price repository to avoid circular imports."""
        if self._price_repo is None:
            from app.services.repositories.price_repository import PriceRepository

            self._price_repo = PriceRepository(self._db)
        return self._price_repo

    def calculate_holding_value(
        self,
        holding: Holding,
        asset: Asset,
        account: Account,
        display_currency: str = "USD",
    ) -> HoldingValue:
        """Calculate value for a single holding.

        Args:
            holding: The holding to value
            asset: The asset (must be pre-loaded)
            account: The account (must be pre-loaded)
            display_currency: Target currency for display values

        Returns:
            HoldingValue with all calculated fields
        """
        asset_currency = asset.currency or "USD"

        # Calculate native currency values
        if asset.asset_class == "Cash":
            # Skip negative cash (liabilities)
            if holding.quantity <= 0:
                market_value_native = Decimal("0")
            else:
                market_value_native = holding.quantity
        else:
            current_price = asset.last_fetched_price or Decimal("0")
            market_value_native = holding.quantity * current_price if current_price else None

        cost_basis_native = holding.cost_basis

        # Calculate P&L in native currency
        if market_value_native is not None and market_value_native > 0:
            pnl_native = market_value_native - cost_basis_native
            pnl_pct = (pnl_native / cost_basis_native * 100) if cost_basis_native > 0 else None
        else:
            pnl_native = None
            pnl_pct = None

        # Convert to display currency
        if asset_currency != display_currency:
            rate = CurrencyService.get_exchange_rate(self._db, asset_currency, display_currency)
            if rate:
                cost_basis = cost_basis_native * rate
                market_value = market_value_native * rate if market_value_native else None
            else:
                cost_basis = cost_basis_native
                market_value = market_value_native
        else:
            cost_basis = cost_basis_native
            market_value = market_value_native

        pnl = (market_value - cost_basis) if market_value is not None else None

        return HoldingValue(
            holding_id=holding.id,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            institution=account.institution,
            quantity=holding.quantity,
            cost_basis_native=cost_basis_native,
            market_value_native=market_value_native,
            pnl_native=pnl_native,
            pnl_pct=pnl_pct,
            cost_basis=cost_basis,
            market_value=market_value,
            pnl=pnl,
            strategy_horizon=holding.strategy_horizon,
        )

    def calculate_day_change(
        self,
        asset: Asset,
        current_price: Decimal | None,
        today: date | None = None,
    ) -> DayChangeResult:
        """Calculate day change for an asset.

        Args:
            asset: The asset
            current_price: Current price (or latest close if market closed)
            today: Date to calculate from (default: today)

        Returns:
            DayChangeResult with day change values
        """
        from app.services.portfolio.trading_calendar_service import TradingCalendarService

        if today is None:
            today = date.today()

        # Cash has no day change
        if asset.asset_class == "Cash":
            return DayChangeResult(
                day_change=None,
                day_change_pct=None,
                previous_close_price=None,
                day_change_date=None,
                is_market_closed=False,
            )

        # Determine market status
        if asset.asset_class == "Crypto":
            is_market_closed = False
        else:
            market = TradingCalendarService.get_market_for_symbol(asset.symbol)
            is_market_closed = TradingCalendarService.is_market_closed(today, market)

        # Get price data
        prices = self.price_repo.find_latest_by_assets([asset.id], limit_per_asset=2)
        asset_prices = prices.get(asset.id, [])

        if is_market_closed:
            # Compare two most recent closes
            if len(asset_prices) >= 2:
                price_for_change = asset_prices[0].closing_price
                previous_close = asset_prices[1].closing_price
                change_date = asset_prices[0].date
            elif len(asset_prices) == 1:
                price_for_change = asset_prices[0].closing_price
                previous_close = None
                change_date = asset_prices[0].date
            else:
                return DayChangeResult(
                    day_change=None,
                    day_change_pct=None,
                    previous_close_price=None,
                    day_change_date=None,
                    is_market_closed=True,
                )
        else:
            # Market open: compare current vs previous close
            price_for_change = current_price
            previous_close = asset_prices[0].closing_price if asset_prices else None
            change_date = today

        # Calculate change
        if previous_close and price_for_change:
            day_change = price_for_change - previous_close
            day_change_pct = (day_change / previous_close) * 100
        else:
            day_change = None
            day_change_pct = None

        return DayChangeResult(
            day_change=day_change,
            day_change_pct=day_change_pct,
            previous_close_price=previous_close,
            day_change_date=str(change_date) if change_date else None,
            is_market_closed=is_market_closed,
        )
