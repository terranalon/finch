"""Trading calendar service for market holiday detection."""

import logging
from datetime import date, timedelta
from functools import lru_cache

import pandas_market_calendars as mcal

logger = logging.getLogger(__name__)


class TradingCalendarService:
    """Service for checking market trading days and holidays."""

    # Map asset suffixes to their market calendars
    MARKET_CALENDARS = {
        ".TA": "TASE",  # Tel Aviv Stock Exchange
        ".TO": "TSX",  # Toronto Stock Exchange
        ".L": "LSE",  # London Stock Exchange
        None: "NYSE",  # Default to NYSE for US stocks
    }

    @staticmethod
    @lru_cache(maxsize=10)
    def _get_calendar(market_name: str):
        """Get a market calendar instance (cached)."""
        try:
            return mcal.get_calendar(market_name)
        except Exception as e:
            logger.warning(f"Failed to get calendar for {market_name}: {e}")
            return None

    @staticmethod
    def get_market_for_symbol(symbol: str | None) -> str:
        """
        Determine which market a symbol belongs to.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "LEUMI.TA")

        Returns:
            Market calendar name (e.g., "NYSE", "TASE")
        """
        if not symbol:
            return "NYSE"

        for suffix, market in TradingCalendarService.MARKET_CALENDARS.items():
            if suffix and symbol.endswith(suffix):
                return market

        return "NYSE"  # Default to NYSE for US stocks

    @staticmethod
    def is_trading_day(check_date: date, market: str = "NYSE") -> bool:
        """
        Check if a given date is a trading day for the specified market.

        Args:
            check_date: Date to check
            market: Market calendar name (default: NYSE)

        Returns:
            True if the market is open on that date, False otherwise
        """
        calendar = TradingCalendarService._get_calendar(market)
        if not calendar:
            # Fallback to simple weekend check if calendar unavailable
            return check_date.weekday() < 5

        try:
            # Get schedule for just that day
            schedule = calendar.schedule(
                start_date=check_date.isoformat(),
                end_date=check_date.isoformat(),
            )
            return not schedule.empty
        except Exception as e:
            logger.warning(f"Error checking trading day for {market}: {e}")
            # Fallback to weekend check
            return check_date.weekday() < 5

    @staticmethod
    def is_market_closed(check_date: date, market: str = "NYSE") -> bool:
        """
        Check if the market is closed on a given date.

        Args:
            check_date: Date to check
            market: Market calendar name (default: NYSE)

        Returns:
            True if the market is closed, False if open
        """
        return not TradingCalendarService.is_trading_day(check_date, market)

    @staticmethod
    def get_previous_trading_day(from_date: date, market: str = "NYSE") -> date | None:
        """
        Get the most recent trading day before the given date.

        Args:
            from_date: Date to search backward from
            market: Market calendar name (default: NYSE)

        Returns:
            The previous trading day, or None if not found within 10 days
        """
        calendar = TradingCalendarService._get_calendar(market)
        if not calendar:
            # Fallback: go back until we find a weekday
            current = from_date - timedelta(days=1)
            for _ in range(10):
                if current.weekday() < 5:
                    return current
                current -= timedelta(days=1)
            return None

        try:
            # Search backward up to 10 days
            start_date = from_date - timedelta(days=10)
            schedule = calendar.schedule(
                start_date=start_date.isoformat(),
                end_date=(from_date - timedelta(days=1)).isoformat(),
            )

            if schedule.empty:
                return None

            # Get the last trading day in the range
            last_trading_day = schedule.index[-1].date()
            return last_trading_day

        except Exception as e:
            logger.warning(f"Error getting previous trading day for {market}: {e}")
            # Fallback to simple weekend skip
            current = from_date - timedelta(days=1)
            for _ in range(10):
                if current.weekday() < 5:
                    return current
                current -= timedelta(days=1)
            return None

    @staticmethod
    def get_trading_days_in_range(
        start_date: date, end_date: date, market: str = "NYSE"
    ) -> list[date]:
        """
        Get all trading days in a date range.

        Args:
            start_date: Start of range
            end_date: End of range
            market: Market calendar name (default: NYSE)

        Returns:
            List of trading days in the range
        """
        calendar = TradingCalendarService._get_calendar(market)
        if not calendar:
            # Fallback: return all weekdays
            days = []
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:
                    days.append(current)
                current += timedelta(days=1)
            return days

        try:
            schedule = calendar.schedule(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return [d.date() for d in schedule.index]
        except Exception as e:
            logger.warning(f"Error getting trading days for {market}: {e}")
            return []

    @staticmethod
    def is_any_market_open(check_date: date) -> bool:
        """
        Check if any major market is open on a given date.

        Useful for determining if we should show "today's movers" or
        fall back to the last trading day's movers.

        Args:
            check_date: Date to check

        Returns:
            True if at least one major market (NYSE, TASE) is open
        """
        markets = ["NYSE", "TASE"]
        for market in markets:
            if TradingCalendarService.is_trading_day(check_date, market):
                return True
        return False
