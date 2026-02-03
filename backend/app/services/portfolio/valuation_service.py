"""Portfolio valuation service - single source of truth for value calculations.

This service centralizes all valuation logic that was previously
duplicated across positions.py and dashboard.py (~200 lines).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.constants import AssetClass
from app.models import Asset
from app.services.portfolio.valuation_types import DayChangeResult

if TYPE_CHECKING:
    from app.services.repositories.price_repository import PriceRepository


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

    def calculate_day_changes_batch(
        self,
        assets: list[Asset],
        current_prices: dict[int, Decimal | None],
        today: date | None = None,
    ) -> dict[int, DayChangeResult]:
        """Calculate day changes for multiple assets in a single batch.

        This method fetches all price data in one query to avoid N+1 problems.

        Args:
            assets: List of assets to calculate day changes for
            current_prices: Map of asset_id -> current price
            today: Date to calculate from (default: today)

        Returns:
            Dict mapping asset_id -> DayChangeResult
        """
        from app.services.portfolio.trading_calendar_service import TradingCalendarService

        if today is None:
            today = date.today()

        if not assets:
            return {}

        # Batch fetch all price data in one query
        asset_ids = [a.id for a in assets]
        all_prices = self.price_repo.find_latest_by_assets(asset_ids, limit_per_asset=2)

        results = {}
        for asset in assets:
            # Cash has no day change
            if asset.asset_class == AssetClass.CASH:
                results[asset.id] = DayChangeResult(
                    day_change=None,
                    day_change_pct=None,
                    previous_close_price=None,
                    day_change_date=None,
                    is_market_closed=False,
                )
                continue

            # Determine market status
            if asset.asset_class == AssetClass.CRYPTO:
                is_market_closed = False
            else:
                market = TradingCalendarService.get_market_for_symbol(asset.symbol)
                is_market_closed = TradingCalendarService.is_market_closed(today, market)

            # Get price data for this asset from the batch result
            asset_prices = all_prices.get(asset.id, [])
            current_price = current_prices.get(asset.id)

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
                    results[asset.id] = DayChangeResult(
                        day_change=None,
                        day_change_pct=None,
                        previous_close_price=None,
                        day_change_date=None,
                        is_market_closed=True,
                    )
                    continue
            else:
                # Market open: compare current vs previous close
                # Filter out today's prices to avoid race condition where today's
                # close is recorded while we're calculating
                price_for_change = current_price
                previous_prices = [p for p in asset_prices if p.date < today]
                previous_close = previous_prices[0].closing_price if previous_prices else None
                change_date = today

            # Calculate change
            if previous_close and price_for_change:
                day_change = price_for_change - previous_close
                day_change_pct = (day_change / previous_close) * 100
            else:
                day_change = None
                day_change_pct = None

            results[asset.id] = DayChangeResult(
                day_change=day_change,
                day_change_pct=day_change_pct,
                previous_close_price=previous_close,
                day_change_date=str(change_date) if change_date else None,
                is_market_closed=is_market_closed,
            )

        return results

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
        if asset.asset_class == AssetClass.CASH:
            return DayChangeResult(
                day_change=None,
                day_change_pct=None,
                previous_close_price=None,
                day_change_date=None,
                is_market_closed=False,
            )

        # Determine market status
        if asset.asset_class == AssetClass.CRYPTO:
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
            # Filter out today's prices to avoid race condition where today's
            # close is recorded while we're calculating
            price_for_change = current_price
            previous_prices = [p for p in asset_prices if p.date < today]
            previous_close = previous_prices[0].closing_price if previous_prices else None
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
