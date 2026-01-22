"""Tests for CoinGecko client."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.coingecko_client import (
    SYMBOL_TO_ID,
    CoinGeckoAPIError,
    CoinGeckoClient,
)


@pytest.fixture
def client():
    """Create CoinGecko client for testing."""
    return CoinGeckoClient()


class TestSymbolMapping:
    """Tests for symbol to CoinGecko ID mapping."""

    def test_common_symbols_mapped(self):
        """Test that common crypto symbols are in the mapping."""
        assert SYMBOL_TO_ID["BTC"] == "bitcoin"
        assert SYMBOL_TO_ID["ETH"] == "ethereum"
        assert SYMBOL_TO_ID["USDC"] == "usd-coin"
        assert SYMBOL_TO_ID["USDT"] == "tether"
        assert SYMBOL_TO_ID["DOGE"] == "dogecoin"

    def test_symbol_to_id_conversion(self, client):
        """Test symbol to ID conversion."""
        assert client._symbol_to_id("BTC") == "bitcoin"
        assert client._symbol_to_id("btc") == "bitcoin"  # Case insensitive
        assert client._symbol_to_id("ETH") == "ethereum"

    def test_symbol_to_id_fallback(self, client):
        """Test fallback to lowercase for unknown symbols."""
        assert client._symbol_to_id("UNKNOWN") == "unknown"
        assert client._symbol_to_id("NewCoin") == "newcoin"

    def test_add_symbol_mapping(self, client):
        """Test adding new symbol mapping."""
        client.add_symbol_mapping("NEWTOKEN", "new-token-id")
        assert SYMBOL_TO_ID["NEWTOKEN"] == "new-token-id"
        assert client._symbol_to_id("NEWTOKEN") == "new-token-id"
        # Cleanup
        del SYMBOL_TO_ID["NEWTOKEN"]


class TestGetCurrentPrices:
    """Tests for get_current_prices method."""

    def test_get_current_prices_success(self, client):
        """Test successful price fetch for multiple symbols."""
        api_response = {
            "bitcoin": {"usd": 42150.32, "last_updated_at": 1705766400},
            "ethereum": {"usd": 2250.15, "last_updated_at": 1705766400},
        }

        with patch.object(client, "_request", return_value=api_response):
            prices = client.get_current_prices(["BTC", "ETH"])

        assert len(prices) == 2
        assert prices["BTC"] == Decimal("42150.32")
        assert prices["ETH"] == Decimal("2250.15")

    def test_get_current_prices_empty_list(self, client):
        """Test with empty symbol list."""
        prices = client.get_current_prices([])
        assert prices == {}

    def test_get_current_prices_partial_response(self, client):
        """Test when some symbols are not found."""
        api_response = {
            "bitcoin": {"usd": 42150.32, "last_updated_at": 1705766400},
            # ethereum missing from response
        }

        with patch.object(client, "_request", return_value=api_response):
            prices = client.get_current_prices(["BTC", "ETH"])

        assert len(prices) == 1
        assert prices["BTC"] == Decimal("42150.32")
        assert "ETH" not in prices

    def test_get_current_prices_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CoinGeckoAPIError("Rate limit exceeded")):
            prices = client.get_current_prices(["BTC"])

        assert prices == {}


class TestGetCurrentPrice:
    """Tests for get_current_price method."""

    def test_get_current_price_success(self, client):
        """Test successful single price fetch."""
        with patch.object(
            client,
            "get_current_prices",
            return_value={"BTC": Decimal("42150.32")},
        ):
            price = client.get_current_price("BTC")

        assert price == Decimal("42150.32")

    def test_get_current_price_not_found(self, client):
        """Test when symbol is not found."""
        with patch.object(client, "get_current_prices", return_value={}):
            price = client.get_current_price("UNKNOWN")

        assert price is None


class TestGetHistoricalPrice:
    """Tests for get_historical_price method."""

    def test_get_historical_price_success(self, client):
        """Test successful historical price fetch."""
        api_response = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "market_data": {"current_price": {"usd": 41235.12, "eur": 38000.0}},
        }

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2024, 1, 15))

        assert price == Decimal("41235.12")

    def test_get_historical_price_no_market_data(self, client):
        """Test when market data is not available."""
        api_response = {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2024, 1, 15))

        assert price is None

    def test_get_historical_price_no_usd_price(self, client):
        """Test when USD price is not available."""
        api_response = {
            "id": "bitcoin",
            "market_data": {"current_price": {"eur": 38000.0}},
        }

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2024, 1, 15))

        assert price is None

    def test_get_historical_price_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CoinGeckoAPIError("Not found", 404)):
            price = client.get_historical_price("UNKNOWN", date(2024, 1, 15))

        assert price is None


class TestGetPriceHistory:
    """Tests for get_price_history method."""

    def test_get_price_history_success(self, client):
        """Test successful price history fetch."""
        api_response = {
            "prices": [
                [1705449600000, 41235.12],
                [1705536000000, 42150.32],
                [1705622400000, 41800.50],
            ],
            "market_caps": [],
            "total_volumes": [],
        }

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("BTC", date(2024, 1, 17), date(2024, 1, 19))

        assert len(history) == 3
        assert all(isinstance(d, date) for d, _ in history)
        assert all(isinstance(p, Decimal) for _, p in history)
        assert history[0][1] == Decimal("41235.12")

    def test_get_price_history_empty(self, client):
        """Test when no price history is available."""
        api_response = {"prices": [], "market_caps": [], "total_volumes": []}

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("BTC", date(2024, 1, 17), date(2024, 1, 19))

        assert history == []

    def test_get_price_history_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CoinGeckoAPIError("Server error", 500)):
            history = client.get_price_history("BTC", date(2024, 1, 17), date(2024, 1, 19))

        assert history == []


class TestGetCoinList:
    """Tests for get_coin_list method."""

    def test_get_coin_list_success(self, client):
        """Test successful coin list fetch."""
        api_response = [
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        ]

        with patch.object(client, "_request", return_value=api_response):
            coins = client.get_coin_list()

        assert len(coins) == 2
        assert coins[0]["id"] == "bitcoin"
        assert coins[1]["symbol"] == "eth"

    def test_get_coin_list_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CoinGeckoAPIError("Server error")):
            coins = client.get_coin_list()

        assert coins == []


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_delay(self, client):
        """Test that rate limiting adds delay between requests."""
        client._min_request_interval = 0.1  # 100ms for faster test
        client._last_request_time = 0

        import time

        start = time.time()
        client._rate_limit()
        client._rate_limit()
        elapsed = time.time() - start

        # Should have delayed at least one interval
        assert elapsed >= 0.09  # Allow small tolerance


class TestAPIConfiguration:
    """Tests for API configuration."""

    def test_explicit_api_key_configuration(self):
        """Test client with explicit API key."""
        client = CoinGeckoClient(api_key="explicit-test-key")
        assert client.api_key == "explicit-test-key"
        assert client.use_pro_api is False
        assert "api.coingecko.com" in client.base_url

    def test_pro_api_configuration(self):
        """Test Pro API configuration."""
        client = CoinGeckoClient(api_key="test-key", use_pro_api=True)
        assert client.api_key == "test-key"
        assert client.use_pro_api is True
        assert "pro-api.coingecko.com" in client.base_url

    def test_headers_with_demo_key(self):
        """Test headers include demo API key."""
        client = CoinGeckoClient(api_key="demo-key", use_pro_api=False)
        headers = client._get_headers()
        assert headers.get("x-cg-demo-api-key") == "demo-key"
        assert "x-cg-pro-api-key" not in headers

    def test_headers_with_pro_key(self):
        """Test headers include Pro API key."""
        client = CoinGeckoClient(api_key="pro-key", use_pro_api=True)
        headers = client._get_headers()
        assert headers.get("x-cg-pro-api-key") == "pro-key"
        assert "x-cg-demo-api-key" not in headers

    def test_headers_with_empty_key(self):
        """Test headers without API key when explicitly empty."""
        client = CoinGeckoClient(api_key="")
        client.api_key = ""  # Force empty even if settings has a value
        headers = client._get_headers()
        assert "x-cg-demo-api-key" not in headers
        assert "x-cg-pro-api-key" not in headers
        assert headers.get("Accept") == "application/json"


class TestCoinGeckoAPIError:
    """Tests for CoinGeckoAPIError exception."""

    def test_error_with_status_code(self):
        """Test error includes status code."""
        error = CoinGeckoAPIError("Rate limit exceeded", status_code=429)
        assert str(error) == "Rate limit exceeded"
        assert error.status_code == 429

    def test_error_without_status_code(self):
        """Test error without status code."""
        error = CoinGeckoAPIError("Network error")
        assert str(error) == "Network error"
        assert error.status_code is None
