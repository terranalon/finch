"""Tests for YFinanceClient rate limiting, batch resolution, and TickerInfo."""

import threading
import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

from app.services.market_data.yfinance_client import (
    QUOTE_TYPE_MAP,
    OHLCVRow,
    TickerInfo,
    YFinanceClient,
    _TokenBucket,
)


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    """Disable rate limiting for all tests, restoring defaults after each test."""
    saved_interval = YFinanceClient._min_request_interval
    saved_time = YFinanceClient._last_request_time
    YFinanceClient._min_request_interval = 0.0
    YFinanceClient._last_request_time = 0.0
    yield
    YFinanceClient._min_request_interval = saved_interval
    YFinanceClient._last_request_time = saved_time


def _make_ticker_info(**overrides: object) -> TickerInfo:
    defaults = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "quote_type": "EQUITY",
        "sector": "Technology",
        "category": None,
        "industry": "Consumer Electronics",
        "currency": "USD",
        "exchange": "NMS",
        "price": Decimal("175.50"),
        "price_timestamp": datetime(2026, 1, 15),
    }
    return TickerInfo(**{**defaults, **overrides})  # ty: ignore[invalid-argument-type]


class TestQuoteTypeMap:
    def test_contains_all_expected_mappings(self):
        assert QUOTE_TYPE_MAP == {
            "ETF": "ETF",
            "MUTUALFUND": "MutualFund",
            "MONEYMARKET": "MoneyMarket",
            "EQUITY": "Stock",
        }


class TestTickerInfoAssetClass:
    def test_equity_maps_to_stock(self):
        info = _make_ticker_info(quote_type="EQUITY")
        assert info.asset_class == "Stock"

    def test_etf_maps_to_etf(self):
        info = _make_ticker_info(quote_type="ETF")
        assert info.asset_class == "ETF"

    def test_mutual_fund(self):
        info = _make_ticker_info(quote_type="MUTUALFUND")
        assert info.asset_class == "MutualFund"

    def test_money_market(self):
        info = _make_ticker_info(quote_type="MONEYMARKET")
        assert info.asset_class == "MoneyMarket"

    def test_unknown_quote_type_returns_none(self):
        info = _make_ticker_info(quote_type="CRYPTOCURRENCY")
        assert info.asset_class is None

    def test_none_quote_type_returns_none(self):
        info = _make_ticker_info(quote_type=None)
        assert info.asset_class is None


class TestRateLimiting:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_consecutive_calls_are_throttled(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.1

        start = time.time()
        client.get_ticker_info("AAPL")
        client.get_ticker_info("MSFT")
        elapsed = time.time() - start

        assert elapsed >= 0.1, f"Expected >= 0.1s, got {elapsed:.3f}s"

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_first_call_not_delayed(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        client = YFinanceClient()

        start = time.time()
        client.get_ticker_info("AAPL")
        elapsed = time.time() - start

        assert elapsed < 0.5


class TestResolveSymbols:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_deduplicates_symbols(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        client = YFinanceClient()

        results = client.resolve_symbols(["AAPL", "MSFT", "AAPL"])

        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results
        # yf.Ticker called only twice (AAPL deduped)
        assert mock_ticker.call_count == 2

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_for_failed_lookups(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()

        results = client.resolve_symbols(["BAD"])

        assert results["BAD"] is None

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_empty_list_returns_empty_dict(self, mock_ticker):
        client = YFinanceClient()
        results = client.resolve_symbols([])
        assert results == {}
        mock_ticker.assert_not_called()

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_preserves_order(self, mock_ticker):
        call_order = []

        def side_effect(symbol):
            call_order.append(symbol)
            mock = type(mock_ticker.return_value)()
            mock.info = {
                "regularMarketPrice": 100.0,
                "quoteType": "EQUITY",
                "longName": f"{symbol} Corp",
            }
            return mock

        mock_ticker.side_effect = side_effect
        client = YFinanceClient()

        results = client.resolve_symbols(["MSFT", "AAPL", "GOOG"])

        assert call_order == ["MSFT", "AAPL", "GOOG"]
        assert list(results.keys()) == ["MSFT", "AAPL", "GOOG"]


class TestOHLCVRow:
    def test_fields(self):
        row = OHLCVRow(
            date=date(2024, 1, 2),
            open=Decimal("150.00"),
            high=Decimal("155.00"),
            low=Decimal("149.00"),
            close=Decimal("153.00"),
            volume=Decimal("1000000"),
        )
        assert row.date == date(2024, 1, 2)
        assert row.close == Decimal("153.00")


class TestGetHistoryForRange:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_ohlcv_rows(self, mock_ticker):
        mock_history = pd.DataFrame(
            {
                "Open": [150.0, 151.0],
                "High": [155.0, 156.0],
                "Low": [149.0, 150.0],
                "Close": [153.0, 154.0],
                "Volume": [1000000, 1100000],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )
        mock_ticker.return_value.history.return_value = mock_history
        client = YFinanceClient()

        rows = client.get_history_for_range("AAPL", date(2024, 1, 2), date(2024, 1, 3))

        assert len(rows) == 2
        assert isinstance(rows[0], OHLCVRow)
        assert rows[0].date == date(2024, 1, 2)
        assert rows[0].close == Decimal("153.0")
        assert rows[0].volume == Decimal("1000000")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_on_no_data(self, mock_ticker):
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()

        rows = client.get_history_for_range("BAD", date(2024, 1, 2), date(2024, 1, 3))
        assert rows == []

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_on_exception(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()

        rows = client.get_history_for_range("ERR", date(2024, 1, 2), date(2024, 1, 3))
        assert rows == []


class TestGetForexRate:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_current_rate(self, mock_ticker):
        mock_history = pd.DataFrame(
            {"Close": [3.70]},
            index=pd.to_datetime(["2024-01-15"]),
        )
        mock_ticker.return_value.history.return_value = mock_history
        client = YFinanceClient()

        rate = client.get_forex_rate("USD", "ILS")

        assert rate == Decimal("3.7")
        mock_ticker.assert_called_with("USDILS=X")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_rate_for_target_date(self, mock_ticker):
        mock_history = pd.DataFrame(
            {"Close": [3.72]},
            index=pd.to_datetime(["2024-01-10"]),
        )
        mock_ticker.return_value.history.return_value = mock_history
        client = YFinanceClient()

        rate = client.get_forex_rate("USD", "ILS", target_date=date(2024, 1, 10))

        assert rate == Decimal("3.72")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_on_empty(self, mock_ticker):
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()

        rate = client.get_forex_rate("USD", "XYZ")
        assert rate is None

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_on_exception(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()

        rate = client.get_forex_rate("USD", "ILS")
        assert rate is None


class TestGetForexHistory:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_ohlcv_rows(self, mock_ticker):
        mock_history = pd.DataFrame(
            {
                "Open": [3.69, 3.70],
                "High": [3.75, 3.76],
                "Low": [3.68, 3.69],
                "Close": [3.70, 3.71],
                "Volume": [0, 0],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )
        mock_ticker.return_value.history.return_value = mock_history
        client = YFinanceClient()

        rows = client.get_forex_history("USD", "ILS", start=date(2024, 1, 2), end=date(2024, 1, 3))

        assert len(rows) == 2
        assert rows[0].close == Decimal("3.7")
        mock_ticker.assert_called_with("USDILS=X")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_on_no_data(self, mock_ticker):
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()

        rows = client.get_forex_history("USD", "XYZ", start=date(2024, 1, 2), end=date(2024, 1, 3))
        assert rows == []


class TestGetHistoricalDataOHLCV:
    """Verify get_historical_data returns OHLCVRow list."""

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_ohlcv_rows(self, mock_ticker):
        mock_history = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [149.0],
                "Close": [153.0],
                "Volume": [1000000],
            },
            index=pd.to_datetime(["2024-01-02"]),
        )
        mock_ticker.return_value.history.return_value = mock_history
        client = YFinanceClient()

        rows = client.get_historical_data("AAPL", period="1mo")

        assert len(rows) == 1
        assert isinstance(rows[0], OHLCVRow)
        assert rows[0].close == Decimal("153.0")


class TestGetCurrentPriceFallbacks:
    """Verify get_current_price tries multiple price fields."""

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_prefers_current_price(self, mock_ticker):
        mock_ticker.return_value.info = {
            "currentPrice": 175.50,
            "regularMarketPrice": 174.00,
            "previousClose": 173.00,
        }
        client = YFinanceClient()

        result = client.get_current_price("AAPL")
        assert result is not None
        assert result[0] == Decimal("175.5")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_falls_back_to_regular_market_price(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 174.00,
            "previousClose": 173.00,
        }
        client = YFinanceClient()

        result = client.get_current_price("AAPL")
        assert result is not None
        assert result[0] == Decimal("174.0")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_falls_back_to_previous_close(self, mock_ticker):
        mock_ticker.return_value.info = {"previousClose": 173.00}
        client = YFinanceClient()

        result = client.get_current_price("AAPL")
        assert result is not None
        assert result[0] == Decimal("173.0")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_when_no_price(self, mock_ticker):
        mock_ticker.return_value.info = {}
        client = YFinanceClient()

        result = client.get_current_price("BAD")
        assert result is None


class TestDataframeToOhlcvRows:
    def test_skips_rows_with_nan_close(self):
        """Rows where Close is NaN should be filtered out entirely."""

        df = pd.DataFrame(
            {
                "Open": [150.0, float("nan")],
                "High": [155.0, float("nan")],
                "Low": [149.0, float("nan")],
                "Close": [153.0, float("nan")],
                "Volume": [1000000, float("nan")],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )
        rows = YFinanceClient._dataframe_to_ohlcv_rows(df)
        assert len(rows) == 1
        assert rows[0].close == Decimal("153.0")

    def test_handles_nan_volume_with_valid_close(self):
        """NaN volume should become 0 when close is valid."""
        df = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [149.0],
                "Close": [153.0],
                "Volume": [float("nan")],
            },
            index=pd.to_datetime(["2024-01-02"]),
        )
        rows = YFinanceClient._dataframe_to_ohlcv_rows(df)
        assert len(rows) == 1
        assert rows[0].volume == Decimal("0")
        assert rows[0].close == Decimal("153.0")


def _single_ticker_df(
    close: float = 153.0,
    dt: str = "2024-01-02",
    *,
    open_: float = 150.0,
    high: float = 155.0,
    low: float = 149.0,
    volume: int = 1000000,
) -> pd.DataFrame:
    """Build a single-ticker OHLCV DataFrame for testing."""
    return pd.DataFrame(
        {
            "Open": [open_],
            "High": [high],
            "Low": [low],
            "Close": [close],
            "Volume": [volume],
        },
        index=pd.to_datetime([dt]),
    )


class TestTokenBucket:
    def test_allows_burst_up_to_capacity(self):
        """Should allow rapid requests up to capacity."""
        bucket = _TokenBucket(rate=10.0, capacity=5)
        start = time.monotonic()
        for _ in range(5):
            bucket.acquire()
        elapsed = time.monotonic() - start
        # 5 tokens available immediately, should be very fast
        assert elapsed < 0.1

    def test_throttles_after_burst(self):
        """Should sleep after burst capacity exhausted."""
        bucket = _TokenBucket(rate=10.0, capacity=1)
        bucket.acquire()  # Consumes the one token
        start = time.monotonic()
        bucket.acquire()  # Should wait ~0.1s for refill
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05

    def test_thread_safety(self):
        """Should handle concurrent access without errors."""
        bucket = _TokenBucket(rate=100.0, capacity=10)
        results: list[bool] = []
        lock = threading.Lock()

        def worker() -> None:
            bucket.acquire()
            with lock:
                results.append(True)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        assert len(results) == 20

    def test_refills_over_time(self):
        """Should refill tokens gradually based on rate."""
        bucket = _TokenBucket(rate=20.0, capacity=5)
        # Drain all tokens
        for _ in range(5):
            bucket.acquire()
        # Wait for ~2 tokens to refill (0.1s at 20/s)
        time.sleep(0.15)
        start = time.monotonic()
        bucket.acquire()  # Should have a token available
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # Should not need to wait


class TestGetBatchPricesThreaded:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_dict_of_ohlcv_rows(self, mock_ticker_cls):
        """Should return OHLCVRow for each successful ticker."""
        mock_ticker_cls.return_value.history.return_value = _single_ticker_df(close=153.0)
        client = YFinanceClient()

        result = client.get_batch_prices_threaded(["AAPL", "MSFT"], rate=100.0)

        assert len(result) == 2
        assert all(isinstance(v, OHLCVRow) for v in result.values())
        aapl = result["AAPL"]
        msft = result["MSFT"]
        assert aapl is not None and aapl.close == Decimal("153.0")
        assert msft is not None and msft.close == Decimal("153.0")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_for_failed_tickers(self, mock_ticker_cls):
        """Should return None for tickers that raise exceptions."""
        mock_ticker_cls.return_value.history.side_effect = Exception("fail")
        client = YFinanceClient()

        result = client.get_batch_prices_threaded(["BAD1", "BAD2"], rate=100.0)

        assert all(v is None for v in result.values())

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_dict_for_empty_input(self, mock_ticker_cls):
        """Should handle empty symbol list."""
        result = YFinanceClient().get_batch_prices_threaded([])
        assert result == {}
        mock_ticker_cls.assert_not_called()

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_handles_empty_history(self, mock_ticker_cls):
        """Should return None for tickers with empty history."""
        mock_ticker_cls.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()

        result = client.get_batch_prices_threaded(["AAPL"], rate=100.0)

        assert result["AAPL"] is None

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_concurrent_execution(self, mock_ticker_cls):
        """Should execute faster than sequential for many tickers."""

        # Each call takes ~10ms
        def slow_history(**kwargs):
            time.sleep(0.01)
            return _single_ticker_df(close=100.0)

        mock_ticker_cls.return_value.history.side_effect = slow_history
        client = YFinanceClient()
        symbols = [f"SYM{i}" for i in range(20)]

        start = time.monotonic()
        result = client.get_batch_prices_threaded(symbols, rate=1000.0, max_workers=16)
        elapsed = time.monotonic() - start

        assert len(result) == 20
        # Sequential would take 20 * 0.01 = 0.2s minimum
        # Concurrent with 16 workers should be much faster
        assert elapsed < 0.15
