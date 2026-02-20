"""YFinance client wrapper with caching and error handling.

Provides a consistent interface for fetching stock/ETF data from Yahoo Finance.
Note: yfinance has its own HTTP handling, so this doesn't inherit from HTTPClient,
but follows similar patterns for error handling and caching.
"""

import logging
import math
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import yfinance as yf

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

QUOTE_TYPE_MAP: dict[str, str] = {
    "ETF": "ETF",
    "MUTUALFUND": "MutualFund",
    "MONEYMARKET": "MoneyMarket",
    "EQUITY": "Stock",
}


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

    @property
    def asset_class(self) -> str | None:
        """Map quote_type to portfolio asset class."""
        if self.quote_type is None:
            return None
        return QUOTE_TYPE_MAP.get(self.quote_type)


@dataclass
class OHLCVRow:
    """Single row of OHLCV historical data."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass
class TickerMarketData:
    """Rich ticker data from ticker.info for intraday enrichment."""

    symbol: str
    price: Decimal | None
    # OHLCV
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
    # Daily fundamentals
    market_cap: Decimal | None
    pe_ratio: Decimal | None
    forward_pe: Decimal | None
    eps: Decimal | None
    dividend_rate: Decimal | None
    dividend_yield: Decimal | None
    payout_ratio: Decimal | None
    # Slow-changing (stocks)
    description: str | None
    exchange: str | None
    website: str | None
    ceo: str | None
    employees: int | None
    beta: Decimal | None
    avg_volume: int | None
    earnings_date: date | None
    ex_dividend_date: date | None
    target_est: Decimal | None
    week_52_high: Decimal | None
    week_52_low: Decimal | None
    peg_ratio: Decimal | None
    # ETF-specific
    expense_ratio: Decimal | None
    fund_family: str | None
    nav: Decimal | None


class _TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int, jitter: float = 0.0) -> None:
        self._rate = rate  # tokens per second
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._jitter = jitter

    def acquire(self) -> None:
        """Block until a token is available, then optionally sleep for jitter."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity,
                    self._tokens + (now - self._last_refill) * self._rate,
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    break
            time.sleep(1.0 / self._rate)
        if self._jitter > 0:
            time.sleep(random.uniform(0, self._jitter))


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

    _last_request_time: float = 0.0
    _min_request_interval: float = 0.5  # seconds between yfinance requests

    # Fields to try for company name, in order of preference
    NAME_FIELDS = ["longName", "shortName", "name"]

    def _rate_limit(self) -> None:
        """Enforce minimum interval between yfinance API calls."""
        elapsed = time.time() - YFinanceClient._last_request_time
        if elapsed < YFinanceClient._min_request_interval:
            time.sleep(YFinanceClient._min_request_interval - elapsed)
        YFinanceClient._last_request_time = time.time()

    @staticmethod
    def _safe_volume(value: int | float) -> Decimal:
        """Convert a volume value to Decimal, treating NaN as zero."""
        if isinstance(value, float) and math.isnan(value):
            return Decimal(0)
        return Decimal(str(int(value)))

    @staticmethod
    def _dataframe_to_ohlcv_rows(df: "pd.DataFrame") -> list[OHLCVRow]:
        """Convert a pandas DataFrame of historical data to OHLCVRow list."""
        return [
            OHLCVRow(
                date=idx.date(),  # ty: ignore[unresolved-attribute] # pandas Timestamp
                open=Decimal(str(row.get("Open", 0))),
                high=Decimal(str(row.get("High", 0))),
                low=Decimal(str(row.get("Low", 0))),
                close=Decimal(str(close)),
                volume=YFinanceClient._safe_volume(row.get("Volume", 0)),
            )
            for idx, row in df.iterrows()
            if (close := row.get("Close")) is not None
            and not (isinstance(close, float) and math.isnan(close))
        ]

    def get_ticker_info(self, symbol: str) -> TickerInfo | None:
        """Get comprehensive ticker information.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "SPY")

        Returns:
            TickerInfo dataclass or None if symbol not found
        """
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Check if we got valid data
            if not info or info.get("regularMarketPrice") is None:
                logger.warning(f"No data found for symbol {symbol}")
                return None

            # Extract name from various fields (first non-empty, non-symbol match)
            name = None
            for field in self.NAME_FIELDS:
                val = info.get(field)
                if val and (stripped := val.strip()) and stripped != symbol:
                    name = stripped
                    break

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

    # Price fields to try, in order of preference
    PRICE_FIELDS = ["currentPrice", "regularMarketPrice", "previousClose"]

    def get_current_price(self, symbol: str) -> tuple[Decimal, datetime] | None:
        """Get current price for a symbol, trying multiple price fields.

        Tries: currentPrice -> regularMarketPrice -> previousClose

        Args:
            symbol: Ticker symbol

        Returns:
            Tuple of (price, timestamp) or None if not found
        """
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            info = ticker.info

            price = next(
                (info[f] for f in self.PRICE_FIELDS if info.get(f) is not None),
                None,
            )
            if price is None or price <= 0:
                logger.warning(f"No price found for {symbol}")
                return None

            return Decimal(str(price)), datetime.now()

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_historical_data(self, symbol: str, period: str = "1y") -> list[OHLCVRow]:
        """Get historical OHLCV data by period.

        Args:
            symbol: Ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            List of OHLCVRow
        """
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period)

            if history.empty:
                logger.warning(f"No historical data for {symbol}")
                return []

            rows = self._dataframe_to_ohlcv_rows(history)
            logger.info(f"Fetched {len(rows)} historical prices for {symbol}")
            return rows

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []

    def get_dividend_dates(self, symbol: str, period: str = "1y") -> list[str]:
        """Return ISO-format ex-dividend dates within a period where Dividends > 0."""
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period)
            if history.empty or "Dividends" not in history.columns:
                return []
            return [
                idx.strftime("%Y-%m-%d")  # ty: ignore[unresolved-attribute]
                for idx, val in history["Dividends"].items()
                if val > 0
            ]
        except Exception as e:
            logger.error(f"Error fetching dividend dates for {symbol}: {e}")
            return []

    def get_history_for_range(self, symbol: str, start: date, end: date) -> list[OHLCVRow]:
        """Get historical OHLCV data for a date range.

        Args:
            symbol: Ticker symbol
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of OHLCVRow, one per trading day
        """
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            history = ticker.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
            )

            if history.empty:
                logger.warning(f"No historical data for {symbol}")
                return []

            rows = self._dataframe_to_ohlcv_rows(history)
            logger.info(f"Fetched {len(rows)} rows for {symbol}")
            return rows

        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return []

    def get_forex_rate(
        self, from_currency: str, to_currency: str, *, target_date: date | None = None
    ) -> Decimal | None:
        """Get forex exchange rate.

        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "ILS")
            target_date: Specific date for the rate (defaults to current)

        Returns:
            Exchange rate as Decimal, or None if unavailable
        """
        try:
            symbol = f"{from_currency}{to_currency}=X"
            self._rate_limit()
            ticker = yf.Ticker(symbol)

            if target_date is not None:
                hist = ticker.history(
                    start=target_date.isoformat(),
                    end=(target_date + timedelta(days=1)).isoformat(),
                )
            else:
                hist = ticker.history(period="1d")

            if hist.empty:
                logger.warning(f"No forex data for {symbol}")
                return None

            rate = hist["Close"].iloc[-1]
            return Decimal(str(rate))

        except Exception as e:
            logger.error(f"Error fetching forex rate for {from_currency}/{to_currency}: {e}")
            return None

    def get_forex_history(
        self, from_currency: str, to_currency: str, *, start: date, end: date
    ) -> list[OHLCVRow]:
        """Get historical forex rates for a date range.

        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "ILS")
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of OHLCVRow, one per trading day
        """
        symbol = f"{from_currency}{to_currency}=X"
        return self.get_history_for_range(symbol, start, end)

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if a symbol exists in Yahoo Finance.

        Args:
            symbol: Ticker symbol to validate

        Returns:
            True if symbol has valid market data
        """
        try:
            self._rate_limit()
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
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except Exception as e:
            logger.error(f"Error fetching raw info for {symbol}: {e}")
            return {}

    def get_batch_prices_threaded(
        self,
        symbols: list[str],
        *,
        period: str = "1d",
        target_date: date | None = None,
        max_workers: int = 16,
        rate: float = 15.0,
    ) -> dict[str, OHLCVRow | None]:
        """Batch fetch OHLCV data using ThreadPoolExecutor with token bucket.

        Args:
            symbols: List of ticker symbols
            period: yfinance period string (default "1d"), ignored if target_date set
            target_date: Fetch data for a specific date instead of using period
            max_workers: Thread pool size
            rate: Max requests per second

        Returns:
            Dict mapping symbol to OHLCVRow (last row) or None if failed
        """
        if not symbols:
            return {}

        bucket = _TokenBucket(rate=rate, capacity=max(int(rate), 1), jitter=1.0 / rate)

        def fetch_one(symbol: str) -> tuple[str, OHLCVRow | None]:
            try:
                bucket.acquire()
                ticker = yf.Ticker(symbol)
                if target_date is not None:
                    history = ticker.history(
                        start=target_date.isoformat(),
                        end=(target_date + timedelta(days=1)).isoformat(),
                    )
                else:
                    history = ticker.history(period=period)
                if history.empty:
                    return symbol, None
                rows = self._dataframe_to_ohlcv_rows(history)
                return symbol, rows[-1] if rows else None
            except Exception:
                logger.debug("Failed to fetch %s", symbol, exc_info=True)
                return symbol, None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fetch_one, sym): sym for sym in symbols}
            return dict(f.result() for f in as_completed(futures))

    def get_batch_ticker_info(
        self,
        symbols: list[str],
        *,
        max_workers: int = 16,
        rate: float = 15.0,
    ) -> dict[str, TickerMarketData | None]:
        """Batch fetch rich ticker.info data using ThreadPoolExecutor.

        Same concurrency pattern as get_batch_prices_threaded but calls
        ticker.info instead of ticker.history, returning richer data for
        the intraday enrichment flow.

        Args:
            symbols: List of ticker symbols
            max_workers: Thread pool size
            rate: Max requests per second

        Returns:
            Dict mapping symbol to TickerMarketData or None if failed
        """
        if not symbols:
            return {}

        bucket = _TokenBucket(rate=rate, capacity=max(int(rate), 1), jitter=1.0 / rate)

        def fetch_one(symbol: str) -> tuple[str, TickerMarketData | None]:
            try:
                bucket.acquire()
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if not info:
                    return symbol, None
                return symbol, self._parse_ticker_info(symbol, info)
            except Exception:
                logger.debug("Failed to fetch info for %s", symbol, exc_info=True)
                return symbol, None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fetch_one, sym): sym for sym in symbols}
            return dict(f.result() for f in as_completed(futures))

    @staticmethod
    def _safe_decimal(info: dict[str, Any], key: str) -> Decimal | None:
        """Extract a Decimal from info dict, handling None and NaN."""
        val = info.get(key)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return Decimal(str(val))

    @staticmethod
    def _safe_int(info: dict[str, Any], key: str) -> int | None:
        """Extract an int from info dict, handling None."""
        val = info.get(key)
        return None if val is None else int(val)

    @staticmethod
    def _extract_ceo(info: dict[str, Any]) -> str | None:
        """Extract CEO name from companyOfficers list."""
        for officer in info.get("companyOfficers", []):
            title = (officer.get("title") or "").lower()
            if "chief executive" in title or title == "ceo":
                return officer.get("name")
        return None

    @staticmethod
    def _parse_epoch_date(info: dict[str, Any], key: str) -> date | None:
        """Parse a Unix epoch timestamp to date, returning None on failure."""
        val = info.get(key)
        if val is None or val == 0:
            return None
        try:
            return datetime.fromtimestamp(val).date()
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _parse_ticker_info(symbol: str, info: dict[str, Any]) -> TickerMarketData | None:
        """Parse raw ticker.info dict into TickerMarketData.

        Returns None if no valid price found (symbol invalid/delisted).
        """
        _dec = YFinanceClient._safe_decimal
        _int = YFinanceClient._safe_int
        _epoch = YFinanceClient._parse_epoch_date

        price = _dec(info, "regularMarketPrice")
        if price is None:
            return None

        return TickerMarketData(
            symbol=symbol,
            price=price,
            open=_dec(info, "regularMarketOpen"),
            high=_dec(info, "regularMarketDayHigh"),
            low=_dec(info, "regularMarketDayLow"),
            close=price,
            volume=_int(info, "regularMarketVolume"),
            market_cap=_dec(info, "marketCap"),
            pe_ratio=_dec(info, "trailingPE"),
            forward_pe=_dec(info, "forwardPE"),
            eps=_dec(info, "trailingEps"),
            dividend_rate=_dec(info, "dividendRate"),
            dividend_yield=_dec(info, "dividendYield"),
            payout_ratio=_dec(info, "payoutRatio"),
            description=info.get("longBusinessSummary"),
            exchange=info.get("exchange"),
            website=info.get("website"),
            ceo=YFinanceClient._extract_ceo(info),
            employees=_int(info, "fullTimeEmployees"),
            beta=_dec(info, "beta"),
            avg_volume=_int(info, "averageVolume"),
            earnings_date=_epoch(info, "earningsDate"),
            ex_dividend_date=_epoch(info, "exDividendDate"),
            target_est=_dec(info, "targetMeanPrice"),
            week_52_high=_dec(info, "fiftyTwoWeekHigh"),
            week_52_low=_dec(info, "fiftyTwoWeekLow"),
            peg_ratio=_dec(info, "pegRatio"),
            expense_ratio=_dec(info, "annualReportExpenseRatio"),
            fund_family=info.get("fundFamily"),
            nav=_dec(info, "navPrice"),
        )

    def resolve_symbols(self, symbols: list[str]) -> dict[str, TickerInfo | None]:
        """Fetch ticker info for multiple symbols with dedup and rate limiting.

        Args:
            symbols: List of ticker symbols (duplicates handled automatically)

        Returns:
            Dict mapping each unique symbol to its TickerInfo or None
        """
        unique_symbols = list(dict.fromkeys(symbols))
        results = {symbol: self.get_ticker_info(symbol) for symbol in unique_symbols}

        resolved_count = sum(1 for v in results.values() if v is not None)
        logger.info("Resolved %d/%d symbols", resolved_count, len(unique_symbols))
        return results
