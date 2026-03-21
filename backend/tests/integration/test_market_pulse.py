"""Integration tests for GET /api/dashboard/market-pulse."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from app.services.market_data.yfinance_client import OHLCVRow


def _mock_ohlcv(close: float) -> OHLCVRow:
    return OHLCVRow(
        date=date(2026, 3, 5),
        open=Decimal(str(close)),
        high=Decimal(str(close)),
        low=Decimal(str(close)),
        close=Decimal(str(close)),
        volume=Decimal("1000000"),
    )


class TestMarketPulse:
    """Test /api/dashboard/market-pulse endpoint."""

    def test_market_pulse_requires_auth(self, client):
        response = client.get("/api/dashboard/market-pulse")
        assert response.status_code == 401

    @patch("app.services.portfolio.market_pulse_service.YFinanceClient")
    def test_market_pulse_returns_structure(self, mock_yf_cls, auth_client):
        mock_client = mock_yf_cls.return_value
        mock_client.get_historical_data.return_value = [
            _mock_ohlcv(500.0 + i * 4) for i in range(5)
        ]

        response = auth_client.get("/api/dashboard/market-pulse")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

        item = data["items"][0]
        assert "symbol" in item
        assert "name" in item
        assert "price" in item
        assert "sparkline" in item
        assert isinstance(item["sparkline"], list)

    @patch("app.services.portfolio.market_pulse_service.YFinanceClient")
    def test_market_pulse_handles_empty_data(self, mock_yf_cls, auth_client):
        mock_client = mock_yf_cls.return_value
        mock_client.get_historical_data.return_value = []

        response = auth_client.get("/api/dashboard/market-pulse")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
