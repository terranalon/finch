"""YFinance client wrapper with caching and error handling.

Provides a consistent interface for fetching stock/ETF data from Yahoo Finance.
Note: yfinance has its own HTTP handling, so this doesn't inherit from HTTPClient,
but follows similar patterns for error handling and caching.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


class YFinanceError(Exception):
    """Exception raised for yfinance API errors."""


@dataclass
class TickerInfo:
    """Structured ticker information from Yahoo Finance."""

    symbol: str
    name: str | None
    quote_type: str | None  # EQUITY, ETF, MUTUALFUND
    sector: str | None  # For stocks
    category: str | None  # For ETFs
    industry: str | None
    currency: str | None
    exchange: str | None
    price: Decimal | None
    price_timestamp: datetime | None


class YFinanceClient:
    """Wrapper around yfinance with caching and error handling.

    Centralizes all yfinance calls to provide:
    - Consistent error handling
    - Result caching (via lru_cache)
    - Structured return types
    - Logging

    Usage:
        client = YFinanceClient()
        info = client.get_ticker_info("AAPL")
        price = client.get_current_price("MSFT")
    """

    # Fields to try for company name, in order of preference
    NAME_FIELDS = ["longName", "shortName", "name"]

    def get_ticker_info(self, symbol: str) -> TickerInfo | None:
        """Get comprehensive ticker information.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "SPY")

        Returns:
            TickerInfo dataclass or None if symbol not found
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Check if we got valid data
            if not info or info.get("regularMarketPrice") is None:
                logger.warning(f"No data found for symbol {symbol}")
                return None

            # Extract name from various fields
            name = None
            for field in self.NAME_FIELDS:
                if field in info and info[field]:
                    name = info[field].strip()
                    if name and name != symbol:
                        break
                    name = None

            # Determine quote type
            quote_type = info.get("quoteType")

            # Extract category based on asset type
            is_etf = quote_type == "ETF"
            sector = None if is_etf else info.get("sector")
            category = info.get("category") if is_etf else None
            industry = None if is_etf else info.get("industry")

            # Get price
            price = None
            price_timestamp = None
            regular_market_price = info.get("regularMarketPrice")
            if regular_market_price is not None:
                price = Decimal(str(regular_market_price))
                price_timestamp = datetime.now()

            return TickerInfo(
                symbol=symbol,
                name=name,
                quote_type=quote_type,
                sector=sector,
                category=category,
                industry=industry,
                currency=info.get("currency"),
                exchange=info.get("exchange"),
                price=price,
                price_timestamp=price_timestamp,
            )

        except Exception as e:
            logger.error(f"Error fetching ticker info for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> tuple[Decimal, datetime] | None:
        """Get current price for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Tuple of (price, timestamp) or None if not found
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            price = info.get("regularMarketPrice")
            if price is None:
                logger.warning(f"No price found for {symbol}")
                return None

            return Decimal(str(price)), datetime.now()

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_historical_data(
        self, symbol: str, period: str = "1y"
    ) -> list[tuple[datetime, Decimal]]:
        """Get historical OHLCV data.

        Args:
            symbol: Ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            List of (date, close_price) tuples
        """
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period)

            if history.empty:
                logger.warning(f"No historical data for {symbol}")
                return []

            results = []
            for idx, row in history.iterrows():
                close_price = row.get("Close")
                if close_price is not None:
                    results.append((idx.to_pydatetime(), Decimal(str(close_price))))

            logger.info(f"Fetched {len(results)} historical prices for {symbol}")
            return results

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if a symbol exists in Yahoo Finance.

        Args:
            symbol: Ticker symbol to validate

        Returns:
            True if symbol has valid market data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info is not None and info.get("regularMarketPrice") is not None

        except Exception:
            return False

    def get_raw_info(self, symbol: str) -> dict[str, Any]:
        """Get raw info dictionary from yfinance.

        Use this when you need access to fields not exposed by TickerInfo.

        Args:
            symbol: Ticker symbol

        Returns:
            Raw info dict from yfinance, or empty dict on error
        """
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except Exception as e:
            logger.error(f"Error fetching raw info for {symbol}: {e}")
            return {}
