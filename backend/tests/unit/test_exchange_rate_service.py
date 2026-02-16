"""Tests for ExchangeRateService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.market_data.exchange_rate_service import ExchangeRateService


class TestRefresh:
    def test_fetches_and_stores_rate(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_yf_client = MagicMock()
        mock_yf_client.get_forex_rate.return_value = Decimal("3.70")

        service = ExchangeRateService(yf_client=mock_yf_client)
        result = service.refresh(mock_db, target_date=date(2024, 1, 10))

        assert result["updated"] > 0
        assert mock_yf_client.get_forex_rate.call_count > 0

    def test_skips_existing_rates(self):
        mock_existing = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing

        mock_yf_client = MagicMock()
        service = ExchangeRateService(yf_client=mock_yf_client)
        result = service.refresh(mock_db, target_date=date(2024, 1, 10))

        assert result["skipped"] == len(service.CURRENCY_PAIRS)
        mock_yf_client.get_forex_rate.assert_not_called()

    def test_handles_api_failure(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_yf_client = MagicMock()
        mock_yf_client.get_forex_rate.return_value = None

        service = ExchangeRateService(yf_client=mock_yf_client)
        result = service.refresh(mock_db, target_date=date(2024, 1, 10))

        assert result["failed"] == len(service.CURRENCY_PAIRS)
