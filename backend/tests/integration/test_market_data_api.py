"""Integration tests for market data refresh endpoints."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models import User
from app.services.auth.auth_service import AuthService


@pytest.fixture
def service_account(db):
    """Create a service account user."""
    user = User(
        email="test-service@system.internal",
        username="svc_market",
        password_hash=AuthService.hash_password("test-password"),
        is_active=True,
        email_verified=True,
        is_service_account=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def service_client(client, service_account):
    """Client authenticated as a service account."""
    token = AuthService.create_access_token(user_id=str(service_account.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestMarketDataAuthRequirements:
    """Test authentication and authorization for market data endpoints."""

    def test_exchange_rates_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/exchange-rates/refresh")
        assert response.status_code == 401

    def test_stock_prices_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/stock-prices/refresh")
        assert response.status_code == 401

    def test_crypto_prices_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/crypto-prices/refresh")
        assert response.status_code == 401

    def test_exchange_rates_requires_service_account(self, auth_client):
        """Regular user cannot access refresh endpoints."""
        response = auth_client.post("/api/market-data/exchange-rates/refresh")
        assert response.status_code == 403
        assert "service account" in response.json()["detail"].lower()

    def test_stock_prices_requires_service_account(self, auth_client):
        """Regular user cannot access refresh endpoints."""
        response = auth_client.post("/api/market-data/stock-prices/refresh")
        assert response.status_code == 403

    def test_crypto_prices_requires_service_account(self, auth_client):
        """Regular user cannot access refresh endpoints."""
        response = auth_client.post("/api/market-data/crypto-prices/refresh")
        assert response.status_code == 403


class TestExchangeRateRefresh:
    """Test exchange rate refresh endpoint with service account."""

    @patch("app.services.market_data.exchange_rate_service.YFinanceClient")
    def test_refresh_success(self, mock_client_cls, service_client):
        """Service account can refresh exchange rates."""
        mock_client = mock_client_cls.return_value
        mock_client.get_forex_rate.return_value = Decimal("3.65")

        yesterday = date.today() - timedelta(days=1)
        response = service_client.post(
            "/api/market-data/exchange-rates/refresh",
            params={"target_date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert "updated" in data
        assert "skipped" in data
        assert "pairs" in data

    @patch("app.services.market_data.exchange_rate_service.YFinanceClient")
    def test_defaults_to_yesterday(self, mock_client_cls, service_client):
        """Date defaults to yesterday when not provided."""
        mock_client = mock_client_cls.return_value
        mock_client.get_forex_rate.return_value = None

        response = service_client.post("/api/market-data/exchange-rates/refresh")

        assert response.status_code == 200
        expected_date = date.today() - timedelta(days=1)
        assert response.json()["date"] == str(expected_date)


class TestStockPriceRefresh:
    """Test stock price refresh endpoint with service account."""

    @patch("app.services.market_data.daily_price_service.YFinanceClient")
    def test_refresh_success(self, mock_client_cls, service_client):
        """Service account can refresh stock prices."""
        mock_client = mock_client_cls.return_value
        mock_client.get_history_for_range.return_value = []

        yesterday = date.today() - timedelta(days=1)
        response = service_client.post(
            "/api/market-data/stock-prices/refresh",
            params={"target_date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert data["source"] == "yfinance"


class TestCryptoPriceRefresh:
    """Test crypto price refresh endpoint with service account."""

    @patch("app.services.market_data.daily_price_service.CoinGeckoClient")
    def test_refresh_success(self, mock_client_class, service_client):
        """Service account can refresh crypto prices."""
        mock_client = MagicMock()
        mock_client.get_historical_price.return_value = None
        mock_client_class.return_value = mock_client

        yesterday = date.today() - timedelta(days=1)
        response = service_client.post(
            "/api/market-data/crypto-prices/refresh",
            params={"target_date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert data["source"] == "coingecko"
