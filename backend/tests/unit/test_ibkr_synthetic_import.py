"""Tests for IBKR synthetic snapshot import service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import Account
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService

AAPL_POSITION = {
    "symbol": "AAPL",
    "original_symbol": "AAPL",
    "description": "APPLE INC",
    "asset_category": "STK",
    "asset_class": "Stock",
    "listing_exchange": "NASDAQ",
    "quantity": Decimal("100"),
    "cost_basis": Decimal("15000"),
    "currency": "USD",
    "account_id": "U12345",
    "needs_validation": False,
    "cusip": "037833100",
    "isin": "US0378331005",
    "conid": "265598",
    "figi": None,
}

MSFT_POSITION = {
    "symbol": "MSFT",
    "original_symbol": "MSFT",
    "description": "MICROSOFT CORP",
    "asset_category": "STK",
    "asset_class": "Stock",
    "listing_exchange": "NASDAQ",
    "quantity": Decimal("50"),
    "cost_basis": Decimal("20000"),
    "currency": "USD",
    "account_id": "U12345",
    "needs_validation": False,
    "cusip": None,
    "isin": None,
    "conid": None,
    "figi": None,
}

USD_CASH_BALANCE = {
    "symbol": "USD",
    "currency": "USD",
    "balance": Decimal("5000"),
    "description": "US Dollar",
    "asset_class": "Cash",
}


def _find_added_synthetic_source(mock_db: MagicMock):
    """Find the BrokerDataSource with source_type='synthetic' from db.add calls."""
    for call in mock_db.add.call_args_list:
        obj = call[0][0]
        if hasattr(obj, "source_type") and obj.source_type == "synthetic":
            return obj
    return None


@pytest.fixture
def mock_db_with_account():
    """Create a mock DB session with a valid account query result."""
    mock_db = MagicMock(spec=Session)
    mock_account = MagicMock(spec=Account)
    mock_account.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_account
    return mock_db


class TestSyntheticImportService:
    """Tests for IBKRSyntheticImportService."""

    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_synthetic_source(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct, mock_db_with_account
    ):
        """import_snapshot should create a BrokerDataSource with source_type='synthetic'."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [AAPL_POSITION]
        mock_parser.extract_cash_balances.return_value = [USD_CASH_BALANCE]

        mock_import_service._import_cash_balances.return_value = {"holdings_created": 1}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "completed"
        assert stats["source_type"] == "synthetic"

        source_added = _find_added_synthetic_source(mock_db_with_account)
        assert source_added is not None
        assert source_added.source_type == "synthetic"

    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_buy_transactions_from_positions(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct, mock_db_with_account
    ):
        """Each position should generate a synthetic Buy transaction."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [AAPL_POSITION, MSFT_POSITION]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 2}

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["positions_imported"] == 2

    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_stores_snapshot_data_for_validation(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct, mock_db_with_account
    ):
        """Snapshot data should be stored in import_stats for later validation."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [
            {**AAPL_POSITION, "isin": None, "conid": None}
        ]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}

        IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        source_added = _find_added_synthetic_source(mock_db_with_account)
        assert source_added is not None
        assert "snapshot_positions" in source_added.import_stats
        snapshot = source_added.import_stats["snapshot_positions"]
        assert len(snapshot) == 1
        assert snapshot[0]["symbol"] == "AAPL"
        assert snapshot[0]["quantity"] == "100"
        assert snapshot[0]["cost_basis"] == "15000"

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_fails_gracefully_on_api_error(self, mock_client, mock_db_with_account):
        """Should return failed status when Flex API returns no data."""
        mock_client.fetch_flex_report.return_value = None

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "failed"
