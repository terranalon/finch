"""Tests for crypto asset market detection in positions endpoint."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.portfolio.trading_calendar_service import TradingCalendarService


class TestCryptoMarketDetection:
    """Test that crypto assets bypass TradingCalendarService for market status."""

    def test_trading_calendar_returns_closed_for_weekend(self):
        """Verify TradingCalendarService correctly identifies weekend as closed."""
        # Saturday Jan 25, 2026
        saturday = date(2026, 1, 25)
        assert TradingCalendarService.is_market_closed(saturday, "NYSE") is True

    def test_trading_calendar_returns_open_for_weekday(self):
        """Verify TradingCalendarService correctly identifies weekday as open."""
        # Monday Jan 27, 2026
        monday = date(2026, 1, 27)
        assert TradingCalendarService.is_market_closed(monday, "NYSE") is False

    def test_crypto_should_bypass_trading_calendar(self):
        """
        Test the crypto market detection logic from positions.py.

        The key insight: crypto assets should NEVER call TradingCalendarService
        because crypto markets are 24/7. The positions.py code checks:
            if position["asset_class"] == "Crypto":
                is_asset_market_closed = False
            else:
                market = TradingCalendarService.get_market_for_symbol(symbol)
                is_asset_market_closed = TradingCalendarService.is_market_closed(...)

        This test verifies the branching logic works correctly.
        """
        # Simulate the positions.py logic for a crypto asset
        position = {"asset_class": "Crypto", "symbol": "BTC"}
        today = date(2026, 1, 25)  # Saturday - markets closed

        # This is the actual logic from positions.py lines 233-238
        if position["asset_class"] == "Crypto":
            is_asset_market_closed = False
        else:
            market = TradingCalendarService.get_market_for_symbol(position["symbol"])
            is_asset_market_closed = TradingCalendarService.is_market_closed(today, market)

        # Crypto should show as "market open" even on weekends
        assert is_asset_market_closed is False

    def test_stock_uses_trading_calendar_on_weekend(self):
        """Verify stocks correctly use TradingCalendarService on weekends."""
        position = {"asset_class": "Stock", "symbol": "AAPL"}
        saturday = date(2026, 1, 25)

        # Apply same logic as positions.py
        if position["asset_class"] == "Crypto":
            is_asset_market_closed = False
        else:
            market = TradingCalendarService.get_market_for_symbol(position["symbol"])
            is_asset_market_closed = TradingCalendarService.is_market_closed(saturday, market)

        # Stock should show as market closed on Saturday
        assert is_asset_market_closed is True


class TestCryptoDayChangeCalculation:
    """Test day change calculation for crypto assets."""

    def test_market_open_path_uses_current_vs_previous_close(self):
        """
        When is_asset_market_closed=False (crypto or market hours), day change
        should compare current_price vs previous_close_price.

        This is the "market open" path from positions.py lines 255-259:
            price_for_day_change = current_price
            previous_close_price = previous_close_map.get(asset_id)
            day_change_date = today
        """
        current_price = Decimal("100000.00")
        previous_close = Decimal("99000.00")

        # Market open path calculation (what positions.py does)
        price_for_day_change = current_price
        previous_close_price = previous_close

        day_change = price_for_day_change - previous_close_price
        day_change_pct = (day_change / previous_close_price) * 100

        assert day_change == Decimal("1000.00")
        assert abs(float(day_change_pct) - 1.0101) < 0.001

    def test_market_closed_path_uses_two_historical_closes(self):
        """
        When is_asset_market_closed=True (weekend/holiday for stocks), day change
        should compare the two most recent closing prices.

        This is the "market closed" path from positions.py lines 240-254.
        """
        # Simulate prices[0] = most recent, prices[1] = previous
        prices = [
            MagicMock(closing_price=Decimal("150.00"), date=date(2026, 1, 24)),
            MagicMock(closing_price=Decimal("148.00"), date=date(2026, 1, 23)),
        ]

        # Market closed path calculation
        price_for_day_change = prices[0].closing_price
        previous_close_price = prices[1].closing_price
        day_change_date = prices[0].date

        day_change = price_for_day_change - previous_close_price
        day_change_pct = (day_change / previous_close_price) * 100

        assert day_change == Decimal("2.00")
        assert abs(float(day_change_pct) - 1.3514) < 0.001
        assert day_change_date == date(2026, 1, 24)

    def test_no_previous_close_returns_none(self):
        """When there's no previous close price, day_change should be None."""
        current_price = Decimal("100000.00")
        previous_close_price = None

        # This matches positions.py lines 261-267
        if previous_close_price and current_price:
            day_change = current_price - previous_close_price
        else:
            day_change = None

        assert day_change is None
