"""Tests for CryptoCompare client."""

import time
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.cryptocompare_client import (
    CryptoCompareAPIError,
    CryptoCompareClient,
)


@pytest.fixture
def client():
    """Create CryptoCompare client for testing."""
    return CryptoCompareClient()


class TestGetHistoricalPrice:
    """Tests for get_historical_price method."""

    def test_get_historical_price_success(self, client):
        """Test successful historical price fetch."""
        api_response = {
            "Response": "Success",
            "Data": {
                "TimeFrom": 1609459200,
                "TimeTo": 1609545600,
                "Data": [
                    {
                        "time": 1609459200,
                        "close": 29000.50,
                        "open": 28500.0,
                        "high": 29500.0,
                        "low": 28000.0,
                    },
                    {
                        "time": 1609545600,
                        "close": 29500.75,
                        "open": 29000.0,
                        "high": 30000.0,
                        "low": 28500.0,
                    },
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2021, 1, 1))

        assert price == Decimal("29000.50")

    def test_get_historical_price_returns_last_available(self, client):
        """Test that last available price is returned when exact date not found."""
        api_response = {
            "Response": "Success",
            "Data": {
                "Data": [
                    {"time": 1609372800, "close": 28500.0},  # Dec 31, 2020
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2021, 1, 1))

        assert price == Decimal("28500.0")

    def test_get_historical_price_no_data(self, client):
        """Test when no data is available."""
        api_response = {"Response": "Success", "Data": {"Data": []}}

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("UNKNOWN", date(2021, 1, 1))

        assert price is None

    def test_get_historical_price_zero_price_ignored(self, client):
        """Test that zero prices are treated as no data."""
        api_response = {
            "Response": "Success",
            "Data": {
                "Data": [
                    {"time": 1609459200, "close": 0},
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            price = client.get_historical_price("BTC", date(2021, 1, 1))

        assert price is None

    def test_get_historical_price_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CryptoCompareAPIError("Server error")):
            price = client.get_historical_price("BTC", date(2021, 1, 1))

        assert price is None


class TestGetPriceHistory:
    """Tests for get_price_history method."""

    def test_get_price_history_success(self, client):
        """Test successful price history fetch."""
        api_response = {
            "Response": "Success",
            "Data": {
                "Data": [
                    {"time": 1609459200, "close": 29000.50},  # 2021-01-01
                    {"time": 1609545600, "close": 29500.75},  # 2021-01-02
                    {"time": 1609632000, "close": 30000.00},  # 2021-01-03
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("BTC", date(2021, 1, 1), date(2021, 1, 3))

        assert len(history) == 3
        assert all(isinstance(d, date) for d, _ in history)
        assert all(isinstance(p, Decimal) for _, p in history)
        assert history[0] == (date(2021, 1, 1), Decimal("29000.50"))
        assert history[2] == (date(2021, 1, 3), Decimal("30000.00"))

    def test_get_price_history_empty(self, client):
        """Test when no price history is available."""
        api_response = {"Response": "Success", "Data": {"Data": []}}

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("UNKNOWN", date(2021, 1, 1), date(2021, 1, 3))

        assert history == []

    def test_get_price_history_filters_by_date_range(self, client):
        """Test that only dates within range are returned."""
        api_response = {
            "Response": "Success",
            "Data": {
                "Data": [
                    {"time": 1609372800, "close": 28500.0},  # 2020-12-31 - outside range
                    {"time": 1609459200, "close": 29000.50},  # 2021-01-01 - inside range
                    {"time": 1609545600, "close": 29500.75},  # 2021-01-02 - inside range
                    {"time": 1609632000, "close": 30000.00},  # 2021-01-03 - outside range
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("BTC", date(2021, 1, 1), date(2021, 1, 2))

        assert len(history) == 2
        assert history[0][0] == date(2021, 1, 1)
        assert history[1][0] == date(2021, 1, 2)

    def test_get_price_history_removes_duplicates(self, client):
        """Test that duplicate dates are removed."""
        api_response = {
            "Response": "Success",
            "Data": {
                "Data": [
                    {"time": 1609459200, "close": 29000.50},
                    {"time": 1609459200, "close": 29000.50},  # Duplicate
                ],
            },
        }

        with patch.object(client, "_request", return_value=api_response):
            history = client.get_price_history("BTC", date(2021, 1, 1), date(2021, 1, 1))

        assert len(history) == 1

    def test_get_price_history_api_error(self, client):
        """Test handling of API errors."""
        with patch.object(client, "_request", side_effect=CryptoCompareAPIError("Server error")):
            history = client.get_price_history("BTC", date(2021, 1, 1), date(2021, 1, 3))

        assert history == []


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_delay(self, client):
        """Test that rate limiting adds delay between requests."""
        client._min_request_interval = 0.1  # 100ms for faster test
        client._last_request_time = 0

        start = time.time()
        client._rate_limit()
        client._rate_limit()
        elapsed = time.time() - start

        # Should have delayed at least one interval
        assert elapsed >= 0.09  # Allow small tolerance


class TestAPIConfiguration:
    """Tests for API configuration."""

    def test_default_configuration(self):
        """Test default client configuration."""
        client = CryptoCompareClient()
        assert client.api_key is None
        assert "min-api.cryptocompare.com" in client.base_url

    def test_with_api_key(self):
        """Test client with API key."""
        client = CryptoCompareClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_headers_with_api_key(self):
        """Test headers include API key when provided."""
        client = CryptoCompareClient(api_key="test-key")
        headers = client._get_headers()
        assert headers.get("authorization") == "Apikey test-key"

    def test_headers_without_api_key(self):
        """Test headers without API key."""
        client = CryptoCompareClient()
        headers = client._get_headers()
        assert "authorization" not in headers
        assert headers.get("Accept") == "application/json"


class TestCryptoCompareAPIError:
    """Tests for CryptoCompareAPIError exception."""

    def test_error_with_status_code(self):
        """Test error includes status code."""
        error = CryptoCompareAPIError("Rate limit exceeded", status_code=429)
        assert str(error) == "Rate limit exceeded"
        assert error.status_code == 429

    def test_error_without_status_code(self):
        """Test error without status code."""
        error = CryptoCompareAPIError("Network error")
        assert str(error) == "Network error"
        assert error.status_code is None
