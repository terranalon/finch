"""Tests for IBKRFlexImportService.import_all stats."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.brokers.ibkr.models import IBKRPosition


class TestImportAllStats:
    """Tests for IBKRFlexImportService.import_all return stats."""

    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_stats_include_positions_and_cash(self, mock_client, mock_parser, mock_import_service):
        """import_all should return stats with positions and cash."""
        from sqlalchemy.orm import Session

        from app.models import Account
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = "<xml>data</xml>"

        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = [
            IBKRPosition(
                symbol="AAPL",
                original_symbol="AAPL",
                description="APPLE INC",
                asset_category="STK",
                asset_class="Stock",
                listing_exchange="NASDAQ",
                quantity=Decimal("100"),
                cost_basis=Decimal("15000"),
                currency="USD",
                account_id="U12345",
                needs_validation=False,
            ),
        ]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_positions.return_value = {"holdings_created": 1}
        mock_import_service._import_cash_balances.return_value = {"holdings_created": 0}
        mock_import_service._update_asset_prices.return_value = {"updated": 1}

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "completed"
        assert stats["positions"] == {"holdings_created": 1}
        assert stats["cash"] == {"holdings_created": 0}
        assert "AAPL" in stats["symbols_in_file"]
        assert stats["unique_assets_in_file"] == 1

    @patch("app.services.brokers.ibkr.flex_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    def test_import_all_no_date_range_in_stats(self, mock_client, mock_parser, mock_import_service):
        """import_all should not include date_range (API imports positions only, not transactions)."""
        from sqlalchemy.orm import Session

        from app.models import Account
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = "<xml>data</xml>"

        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = []
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_positions.return_value = {}
        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._update_asset_prices.return_value = {}

        stats = IBKRFlexImportService.import_all(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "completed"
        assert "date_range" not in stats

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
