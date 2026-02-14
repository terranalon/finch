"""Tests for IBKRFlexImportService.import_all with transaction support."""

from datetime import date
from unittest.mock import MagicMock, patch


class TestImportAllWithTransactions:
    """Tests for IBKRFlexImportService.import_all with full transaction support."""

    def _setup_mocks(self, mock_client, mock_parser, mock_import_service):
        """Shared setup for import_all mocks."""
        from sqlalchemy.orm import Session

        from app.models import Account

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"

        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_cash_balances.return_value = []
        mock_parser.extract_transactions.return_value = []
        mock_parser.extract_dividends.return_value = []
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []
        mock_parser.extract_other_cash_transactions.return_value = []

        mock_import_service._import_cash_balances.return_value = {"holdings_created": 0}
        mock_import_service._import_transactions.return_value = {"imported": 0}
        mock_import_service._import_dividends.return_value = {"imported": 0}
        mock_import_service._import_transfers.return_value = {"imported": 0}
        mock_import_service._import_forex_transactions.return_value = {"imported": 0}
        mock_import_service._import_other_cash_transactions.return_value = {"imported": 0}
        mock_import_service._import_dividend_cash.return_value = {"imported": 0}
        mock_import_service._update_asset_prices.return_value = {"updated": 0}

        return mock_db

    @patch("app.services.brokers.ibkr.flex_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_passes_start_date_to_flex_client(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_all should pass start_date as from_date to the Flex Query client."""
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = self._setup_mocks(mock_client, mock_parser, mock_import_service)
        mock_reconstruct.return_value = {}

        start = date(2026, 2, 1)
        IBKRFlexImportService.import_all(
            mock_db,
            account_id=1,
            flex_token="tok",
            flex_query_id="qid",
            start_date=start,
        )

        mock_client.fetch_flex_report.assert_called_once_with("tok", "qid", from_date=start)

    @patch("app.services.brokers.ibkr.flex_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_extracts_and_imports_transactions(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_all should extract all transaction types and import them."""
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = self._setup_mocks(mock_client, mock_parser, mock_import_service)
        mock_reconstruct.return_value = {}

        IBKRFlexImportService.import_all(
            mock_db,
            account_id=1,
            flex_token="tok",
            flex_query_id="qid",
        )

        # Verify all extract methods were called
        mock_root = mock_parser.parse_xml.return_value
        mock_parser.extract_transactions.assert_called_once_with(mock_root)
        mock_parser.extract_dividends.assert_called_once_with(mock_root)
        mock_parser.extract_transfers.assert_called_once_with(mock_root)
        mock_parser.extract_forex_transactions.assert_called_once_with(mock_root)
        mock_parser.extract_other_cash_transactions.assert_called_once_with(mock_root)

        # Verify all import methods were called
        mock_import_service._import_transactions.assert_called_once()
        mock_import_service._import_dividends.assert_called_once()
        mock_import_service._import_transfers.assert_called_once()
        mock_import_service._import_forex_transactions.assert_called_once()
        mock_import_service._import_other_cash_transactions.assert_called_once()
        mock_import_service._import_dividend_cash.assert_called_once()

    @patch("app.services.brokers.ibkr.flex_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_does_not_import_positions(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_all should NOT call _import_positions -- holdings come from reconstruction."""
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = self._setup_mocks(mock_client, mock_parser, mock_import_service)
        mock_reconstruct.return_value = {}

        IBKRFlexImportService.import_all(
            mock_db,
            account_id=1,
            flex_token="tok",
            flex_query_id="qid",
        )

        mock_import_service._import_positions.assert_not_called()
        mock_parser.extract_positions.assert_not_called()

    @patch("app.services.brokers.ibkr.flex_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_calls_reconstruction_after_import(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_all should reconstruct holdings from transactions after importing."""
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = self._setup_mocks(mock_client, mock_parser, mock_import_service)
        mock_reconstruct.return_value = {"holdings_updated": 3}

        stats = IBKRFlexImportService.import_all(
            mock_db,
            account_id=1,
            flex_token="tok",
            flex_query_id="qid",
        )

        mock_reconstruct.assert_called_once_with(mock_db, 1)
        assert stats["holdings_reconstruction"] == {"holdings_updated": 3}

    @patch("app.services.brokers.ibkr.flex_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_stats_include_transaction_counts(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_all stats should include counts for all transaction types."""
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = self._setup_mocks(mock_client, mock_parser, mock_import_service)
        mock_reconstruct.return_value = {}
        mock_import_service._import_transactions.return_value = {"imported": 5}
        mock_import_service._import_dividends.return_value = {"imported": 2}

        stats = IBKRFlexImportService.import_all(
            mock_db,
            account_id=1,
            flex_token="tok",
            flex_query_id="qid",
        )

        assert stats["status"] == "completed"
        assert stats["transactions"] == {"imported": 5}
        assert stats["dividends"] == {"imported": 2}
        assert "cash" in stats

    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_import_all_fails_on_bad_account(self, mock_client, mock_parser, mock_import_service):
        """import_all should fail gracefully when account doesn't exist."""
        from sqlalchemy.orm import Session

        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=999, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "failed"
        assert any("not found" in e for e in stats["errors"])
