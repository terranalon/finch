"""Tests for YFinanceClient rate limiting, batch resolution, and TickerInfo."""

import threading
import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from app.services.market_data.yfinance_client import (
    QUOTE_TYPE_MAP,
    OHLCVRow,
    TickerInfo,
    YFinanceClient,
    _TokenBucket,
)


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
        # Override interval for fast testing
        YFinanceClient._min_request_interval = 0.1

        start = time.time()
        client.get_ticker_info("AAPL")
        client.get_ticker_info("MSFT")
        elapsed = time.time() - start

        assert elapsed >= 0.1, f"Expected >= 0.1s, got {elapsed:.3f}s"
        # Restore default
        YFinanceClient._min_request_interval = 0.5

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_first_call_not_delayed(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        # Reset class-level state
        YFinanceClient._last_request_time = 0.0
        client = YFinanceClient()

        start = time.time()
        client.get_ticker_info("AAPL")
        elapsed = time.time() - start

        # First call should not be delayed (< 0.1s unless yf is slow)
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
        YFinanceClient._min_request_interval = 0.0  # skip delay in tests

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

        rows = client.get_history_for_range("BAD", date(2024, 1, 2), date(2024, 1, 3))
        assert rows == []

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_on_exception(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

        rate = client.get_forex_rate("USD", "ILS", target_date=date(2024, 1, 10))

        assert rate == Decimal("3.72")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_on_empty(self, mock_ticker):
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

        rate = client.get_forex_rate("USD", "XYZ")
        assert rate is None

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_on_exception(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

        rows = client.get_forex_history("USD", "ILS", start=date(2024, 1, 2), end=date(2024, 1, 3))

        assert len(rows) == 2
        assert rows[0].close == Decimal("3.7")
        mock_ticker.assert_called_with("USDILS=X")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_empty_on_no_data(self, mock_ticker):
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

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
        YFinanceClient._min_request_interval = 0.0

        result = client.get_current_price("AAPL")
        assert result is not None
        assert result[0] == Decimal("174.0")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_falls_back_to_previous_close(self, mock_ticker):
        mock_ticker.return_value.info = {"previousClose": 173.00}
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

        result = client.get_current_price("AAPL")
        assert result is not None
        assert result[0] == Decimal("173.0")

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_when_no_price(self, mock_ticker):
        mock_ticker.return_value.info = {}
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

        result = client.get_current_price("BAD")
        assert result is None


def _single_ticker_df(
    close: float = 153.0,
    dt: str = "2024-01-02",
    *,
    open_: float = 150.0,
    high: float = 155.0,
    low: float = 149.0,
    volume: int = 1000000,
) -> pd.DataFrame:
    """Build a single-ticker DataFrame matching yf.download() output."""
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


def _multi_ticker_df(tickers: dict[str, float], dt: str = "2024-01-02") -> pd.DataFrame:
    """Build a MultiIndex DataFrame matching yf.download(group_by='ticker')."""
    frames: dict[str, pd.DataFrame] = {}
    idx = pd.to_datetime([dt])
    for sym, close in tickers.items():
        frames[sym] = pd.DataFrame(
            {
                "Open": [close - 3],
                "High": [close + 2],
                "Low": [close - 4],
                "Close": [close],
                "Volume": [1000000],
            },
            index=idx,
        )
    return pd.concat(frames, axis=1)


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


class TestGetBatchPricesDownload:
    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_returns_dict_of_ohlcv_rows(self, mock_download):
        """Should return OHLCVRow for each successful ticker."""
        mock_download.return_value = _multi_ticker_df({"AAPL": 153.0, "MSFT": 400.0})
        client = YFinanceClient()

        result = client.get_batch_prices_download(["AAPL", "MSFT"])

        assert len(result) == 2
        assert isinstance(result["AAPL"], OHLCVRow)
        assert result["AAPL"].close == Decimal("153.0")
        assert isinstance(result["MSFT"], OHLCVRow)
        assert result["MSFT"].close == Decimal("400.0")

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_single_ticker_no_multiindex(self, mock_download):
        """Should handle single-ticker download (no MultiIndex)."""
        mock_download.return_value = _single_ticker_df(close=153.0)
        client = YFinanceClient()

        result = client.get_batch_prices_download(["AAPL"])

        assert len(result) == 1
        assert isinstance(result["AAPL"], OHLCVRow)
        assert result["AAPL"].close == Decimal("153.0")

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_returns_none_for_failed_tickers(self, mock_download):
        """Should return None for tickers with NaN/empty data."""
        # Build frame with only AAPL data, BAD will be missing from MultiIndex
        mock_download.return_value = _multi_ticker_df({"AAPL": 153.0})
        client = YFinanceClient()

        result = client.get_batch_prices_download(["AAPL", "BAD"])

        assert result["AAPL"] is not None
        assert result["BAD"] is None

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_chunks_large_symbol_lists(self, mock_download):
        """Should call yf.download multiple times for lists > chunk_size."""
        mock_download.return_value = pd.DataFrame()
        client = YFinanceClient()
        symbols = [f"SYM{i}" for i in range(600)]

        client.get_batch_prices_download(symbols, chunk_size=250, chunk_delay=0.0)

        assert mock_download.call_count == 3

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_returns_empty_dict_for_empty_input(self, mock_download):
        """Should handle empty symbol list."""
        result = YFinanceClient().get_batch_prices_download([])
        assert result == {}
        mock_download.assert_not_called()

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_handles_download_exception(self, mock_download):
        """Should return None for all tickers when download raises."""
        mock_download.side_effect = Exception("Network error")
        client = YFinanceClient()

        result = client.get_batch_prices_download(["AAPL", "MSFT"])

        assert result["AAPL"] is None
        assert result["MSFT"] is None

    @patch("app.services.market_data.yfinance_client.yf.download")
    def test_handles_none_return(self, mock_download):
        """Should handle yf.download returning None."""
        mock_download.return_value = None
        client = YFinanceClient()

        result = client.get_batch_prices_download(["AAPL"])

        assert result["AAPL"] is None


class TestGetBatchPricesThreaded:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_dict_of_ohlcv_rows(self, mock_ticker_cls):
        """Should return OHLCVRow for each successful ticker."""
        mock_ticker_cls.return_value.history.return_value = _single_ticker_df(close=153.0)
        client = YFinanceClient()

        result = client.get_batch_prices_threaded(["AAPL", "MSFT"], rate=100.0)

        assert len(result) == 2
        assert all(isinstance(v, OHLCVRow) for v in result.values())
        assert result["AAPL"].close == Decimal("153.0")
        assert result["MSFT"].close == Decimal("153.0")

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
