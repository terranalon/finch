"""Tests for CryptoImportService date_range in stats."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)


class TestImportDataReturnsDateRange:
    """Tests for date_range in CryptoImportService.import_data stats."""

    @pytest.fixture
    def mock_service(self):
        """Create a CryptoImportService with all DB operations mocked."""
        with patch("app.services.crypto_import_service.CoinGeckoClient"):
            from app.services.crypto_import_service import CryptoImportService

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_db.query.return_value.filter.return_value.all.return_value = []

            service = CryptoImportService(mock_db, "kraken")

            # Mock all internal methods that touch the DB
            mock_holding = MagicMock()
            mock_holding.id = 1
            service._get_or_create_holding = MagicMock(return_value=mock_holding)
            service._import_transactions = MagicMock(return_value={"imported": 0})
            service._import_cash_transactions = MagicMock(return_value={"imported": 0})
            service._import_dividends = MagicMock(return_value={"imported": 0})
            service._reconstruct_and_update_holdings = MagicMock(return_value={})
            service._create_broker_data_source = MagicMock()

            return service

    def test_stats_include_date_range_from_transactions(self, mock_service):
        """import_data should return date_range calculated from transaction dates."""
        data = BrokerImportData(
            start_date=date(2024, 1, 10),
            end_date=date(2024, 3, 15),
            positions=[],
            transactions=[
                ParsedTransaction(
                    symbol="BTC",
                    trade_date=date(2024, 1, 10),
                    transaction_type="Buy",
                    quantity=Decimal("0.5"),
                    price_per_unit=Decimal("40000"),
                    amount=Decimal("20000"),
                    currency="USD",
                ),
                ParsedTransaction(
                    symbol="ETH",
                    trade_date=date(2024, 3, 15),
                    transaction_type="Buy",
                    quantity=Decimal("2"),
                    price_per_unit=Decimal("3000"),
                    amount=Decimal("6000"),
                    currency="USD",
                ),
            ],
            cash_transactions=[],
            dividends=[],
        )

        mock_service._import_transactions.return_value = {"imported": 2}

        stats = mock_service.import_data(account_id=1, data=data)

        # Should include date_range as ISO strings
        assert "date_range" in stats
        assert stats["date_range"]["start_date"] == "2024-01-10"
        assert stats["date_range"]["end_date"] == "2024-03-15"

    def test_stats_include_date_range_from_cash_transactions(self, mock_service):
        """date_range should include cash transaction dates."""
        data = BrokerImportData(
            start_date=date(2024, 1, 5),
            end_date=date(2024, 4, 20),
            positions=[],
            transactions=[
                ParsedTransaction(
                    symbol="BTC",
                    trade_date=date(2024, 2, 1),
                    transaction_type="Buy",
                    quantity=Decimal("1"),
                    price_per_unit=Decimal("40000"),
                    amount=Decimal("40000"),
                    currency="USD",
                ),
            ],
            cash_transactions=[
                ParsedCashTransaction(
                    date=date(2024, 1, 5),  # Earlier than transaction
                    transaction_type="Deposit",
                    amount=Decimal("50000"),
                    currency="USD",
                ),
                ParsedCashTransaction(
                    date=date(2024, 4, 20),  # Later than transaction
                    transaction_type="Withdrawal",
                    amount=Decimal("-10000"),
                    currency="USD",
                ),
            ],
            dividends=[],
        )

        mock_service._import_transactions.return_value = {"imported": 1}
        mock_service._import_cash_transactions.return_value = {"imported": 2}

        stats = mock_service.import_data(account_id=1, data=data)

        # date_range should span from earliest cash txn to latest cash txn
        assert stats["date_range"]["start_date"] == "2024-01-05"
        assert stats["date_range"]["end_date"] == "2024-04-20"

    def test_stats_include_date_range_from_dividends(self, mock_service):
        """date_range should include dividend dates."""
        # Dividends use ParsedTransaction with transaction_type="Dividend"
        data = BrokerImportData(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 9, 15),
            positions=[],
            transactions=[],
            cash_transactions=[],
            dividends=[
                ParsedTransaction(
                    symbol="AAPL",
                    trade_date=date(2024, 6, 1),
                    transaction_type="Dividend",
                    quantity=Decimal("0"),
                    price_per_unit=Decimal("0"),
                    amount=Decimal("50"),
                    currency="USD",
                ),
                ParsedTransaction(
                    symbol="MSFT",
                    trade_date=date(2024, 9, 15),
                    transaction_type="Dividend",
                    quantity=Decimal("0"),
                    price_per_unit=Decimal("0"),
                    amount=Decimal("30"),
                    currency="USD",
                ),
            ],
        )

        mock_service._import_dividends.return_value = {"imported": 2}

        stats = mock_service.import_data(account_id=1, data=data)

        assert stats["date_range"]["start_date"] == "2024-06-01"
        assert stats["date_range"]["end_date"] == "2024-09-15"

    def test_no_date_range_when_no_transactions(self, mock_service):
        """date_range should not be present when there are no transactions."""
        data = BrokerImportData(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            positions=[],
            transactions=[],
            cash_transactions=[],
            dividends=[],
        )

        stats = mock_service.import_data(account_id=1, data=data)

        # No date_range when there's no data
        assert "date_range" not in stats
