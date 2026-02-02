"""Tests for IBKRFlexImportService date_range in stats."""

from datetime import date
from unittest.mock import MagicMock, patch


class TestImportAllReturnsDateRange:
    """Tests for date_range in IBKRFlexImportService.import_all stats."""

    @patch("app.services.ibkr_flex_import_service.IBKRImportService")
    @patch("app.services.ibkr_flex_import_service.IBKRParser")
    @patch("app.services.ibkr_flex_import_service.IBKRFlexClient")
    def test_stats_include_date_range_from_transactions(
        self, mock_client, mock_parser, mock_import_service
    ):
        """import_all should return date_range calculated from transaction dates."""
        from app.services.ibkr_flex_import_service import IBKRFlexImportService
        from sqlalchemy.orm import Session

        from app.models import Account

        # Create mock session
        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        # Mock client
        mock_client.fetch_flex_report.return_value = "<xml>data</xml>"

        # Mock parser
        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.get_all_section_types.return_value = []
        mock_parser.get_cash_transaction_types.return_value = []
        mock_parser.analyze_fx_transactions.return_value = []
        mock_parser.extract_positions.return_value = []
        mock_parser.extract_cash_balances.return_value = []

        # Transactions with known dates
        mock_parser.extract_transactions.return_value = [
            {"symbol": "AAPL", "date": date(2024, 2, 1), "type": "Buy"},
            {"symbol": "MSFT", "date": date(2024, 4, 15), "type": "Buy"},
        ]
        mock_parser.extract_dividends.return_value = [
            {"symbol": "AAPL", "date": date(2024, 3, 10)},
        ]
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []

        # Mock import service methods
        mock_import_service._import_positions.return_value = {
            "holdings_created": 0,
            "holdings_updated": 0,
        }
        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._import_transactions.return_value = {"imported": 2}
        mock_import_service._import_dividends.return_value = {"imported": 1}
        mock_import_service._import_transfers.return_value = {"imported": 0}
        mock_import_service._import_forex_transactions.return_value = {"imported": 0}
        mock_import_service._update_asset_prices.return_value = {}

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        # Should include date_range as ISO strings
        assert "date_range" in stats
        assert stats["date_range"]["start_date"] == "2024-02-01"
        assert stats["date_range"]["end_date"] == "2024-04-15"

    @patch("app.services.ibkr_flex_import_service.IBKRImportService")
    @patch("app.services.ibkr_flex_import_service.IBKRParser")
    @patch("app.services.ibkr_flex_import_service.IBKRFlexClient")
    def test_date_range_includes_all_data_types(
        self, mock_client, mock_parser, mock_import_service
    ):
        """date_range should include dates from transactions, dividends, transfers, and forex."""
        from app.services.ibkr_flex_import_service import IBKRFlexImportService
        from sqlalchemy.orm import Session

        from app.models import Account

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = "<xml>data</xml>"

        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.get_all_section_types.return_value = []
        mock_parser.get_cash_transaction_types.return_value = []
        mock_parser.analyze_fx_transactions.return_value = []
        mock_parser.extract_positions.return_value = []
        mock_parser.extract_cash_balances.return_value = []

        # Different data types with varying dates
        mock_parser.extract_transactions.return_value = [
            {"symbol": "AAPL", "date": date(2024, 3, 1)},
        ]
        mock_parser.extract_dividends.return_value = [
            {"symbol": "AAPL", "date": date(2024, 1, 15)},  # Earliest
        ]
        mock_parser.extract_transfers.return_value = [
            {"date": date(2024, 5, 20)},  # Latest
        ]
        mock_parser.extract_forex_transactions.return_value = [
            {"date": date(2024, 2, 10)},
        ]

        mock_import_service._import_positions.return_value = {
            "holdings_created": 0,
            "holdings_updated": 0,
        }
        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._import_transactions.return_value = {"imported": 1}
        mock_import_service._import_dividends.return_value = {"imported": 1}
        mock_import_service._import_transfers.return_value = {"imported": 1}
        mock_import_service._import_forex_transactions.return_value = {"imported": 1}
        mock_import_service._update_asset_prices.return_value = {}

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        # date_range should span from dividend (earliest) to transfer (latest)
        assert stats["date_range"]["start_date"] == "2024-01-15"
        assert stats["date_range"]["end_date"] == "2024-05-20"

    @patch("app.services.ibkr_flex_import_service.IBKRImportService")
    @patch("app.services.ibkr_flex_import_service.IBKRParser")
    @patch("app.services.ibkr_flex_import_service.IBKRFlexClient")
    def test_no_date_range_when_no_dated_data(
        self, mock_client, mock_parser, mock_import_service
    ):
        """date_range should not be present when there are no dated transactions."""
        from app.services.ibkr_flex_import_service import IBKRFlexImportService
        from sqlalchemy.orm import Session

        from app.models import Account

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = "<xml>data</xml>"

        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.get_all_section_types.return_value = []
        mock_parser.get_cash_transaction_types.return_value = []
        mock_parser.analyze_fx_transactions.return_value = []
        mock_parser.extract_positions.return_value = [{"symbol": "AAPL"}]  # No date
        mock_parser.extract_cash_balances.return_value = []
        mock_parser.extract_transactions.return_value = []
        mock_parser.extract_dividends.return_value = []
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []

        mock_import_service._import_positions.return_value = {
            "holdings_created": 1,
            "holdings_updated": 0,
        }
        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._import_transactions.return_value = {"imported": 0}
        mock_import_service._import_dividends.return_value = {"imported": 0}
        mock_import_service._import_transfers.return_value = {"imported": 0}
        mock_import_service._import_forex_transactions.return_value = {"imported": 0}
        mock_import_service._update_asset_prices.return_value = {}

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        # No date_range when there's no dated data
        assert "date_range" not in stats
