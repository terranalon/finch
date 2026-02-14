"""Tests for IBKRFlexImportService.import_all with transaction support."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

MODULE = "app.services.brokers.ibkr.flex_import_service"


@pytest.fixture()
def flex_import_mocks():
    """Patch all external dependencies for IBKRFlexImportService.import_all."""
    from sqlalchemy.orm import Session

    from app.models import Account

    with (
        patch(f"{MODULE}.IBKRFlexClient") as mock_client,
        patch(f"{MODULE}.IBKRParser") as mock_parser,
        patch(f"{MODULE}.IBKRImportService") as mock_import_service,
        patch(f"{MODULE}.reconstruct_and_update_holdings") as mock_reconstruct,
    ):
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

        mock_reconstruct.return_value = {}

        yield {
            "db": mock_db,
            "client": mock_client,
            "parser": mock_parser,
            "import_service": mock_import_service,
            "reconstruct": mock_reconstruct,
        }


def _run_import(mocks, **overrides):
    """Call import_all with standard arguments, allowing per-test overrides."""
    from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

    kwargs = {
        "db": mocks["db"],
        "account_id": 1,
        "flex_token": "tok",
        "flex_query_id": "qid",
        **overrides,
    }
    return IBKRFlexImportService.import_all(**kwargs)


class TestImportAllWithTransactions:
    """Tests for IBKRFlexImportService.import_all with full transaction support."""

    def test_passes_start_date_to_flex_client(self, flex_import_mocks):
        """import_all should pass start_date as from_date to the Flex Query client."""
        start = date(2026, 2, 1)
        _run_import(flex_import_mocks, start_date=start)

        flex_import_mocks["client"].fetch_flex_report.assert_called_once_with(
            "tok", "qid", from_date=start
        )

    def test_extracts_and_imports_transactions(self, flex_import_mocks):
        """import_all should extract all transaction types and import them."""
        _run_import(flex_import_mocks)

        mock_parser = flex_import_mocks["parser"]
        mock_root = mock_parser.parse_xml.return_value
        mock_parser.extract_transactions.assert_called_once_with(mock_root)
        mock_parser.extract_dividends.assert_called_once_with(mock_root)
        mock_parser.extract_transfers.assert_called_once_with(mock_root)
        mock_parser.extract_forex_transactions.assert_called_once_with(mock_root)
        mock_parser.extract_other_cash_transactions.assert_called_once_with(mock_root)

        mock_import = flex_import_mocks["import_service"]
        mock_import._import_transactions.assert_called_once()
        mock_import._import_dividends.assert_called_once()
        mock_import._import_transfers.assert_called_once()
        mock_import._import_forex_transactions.assert_called_once()
        mock_import._import_other_cash_transactions.assert_called_once()
        mock_import._import_dividend_cash.assert_called_once()

    def test_does_not_import_positions(self, flex_import_mocks):
        """import_all should NOT call _import_positions -- holdings come from reconstruction."""
        _run_import(flex_import_mocks)

        flex_import_mocks["import_service"]._import_positions.assert_not_called()
        flex_import_mocks["parser"].extract_positions.assert_not_called()

    def test_calls_reconstruction_after_import(self, flex_import_mocks):
        """import_all should reconstruct holdings from transactions after importing."""
        flex_import_mocks["reconstruct"].return_value = {"holdings_updated": 3}

        stats = _run_import(flex_import_mocks)

        flex_import_mocks["reconstruct"].assert_called_once_with(flex_import_mocks["db"], 1)
        assert stats["holdings_reconstruction"] == {"holdings_updated": 3}

    def test_stats_include_transaction_counts(self, flex_import_mocks):
        """import_all stats should include counts for all transaction types."""
        mock_import = flex_import_mocks["import_service"]
        mock_import._import_transactions.return_value = {"imported": 5}
        mock_import._import_dividends.return_value = {"imported": 2}

        stats = _run_import(flex_import_mocks)

        assert stats["status"] == "completed"
        assert stats["transactions"] == {"imported": 5}
        assert stats["dividends"] == {"imported": 2}
        assert "cash" in stats

    def test_import_all_fails_on_bad_account(self, flex_import_mocks):
        """import_all should fail gracefully when account doesn't exist."""
        flex_import_mocks["db"].query.return_value.filter.return_value.first.return_value = None

        stats = _run_import(flex_import_mocks, account_id=999)

        assert stats["status"] == "failed"
        assert any("not found" in e for e in stats["errors"])


STAGED_MODULE = "app.services.shared.staged_import_service"


@pytest.fixture()
def staged_import_mocks():
    """Patch all external dependencies for StagedImportService.import_with_staging."""
    from sqlalchemy.orm import Session

    from app.models import Account

    with (
        patch(f"{STAGED_MODULE}.create_staging_tables"),
        patch(f"{STAGED_MODULE}.copy_production_to_staging", return_value={}),
        patch(f"{STAGED_MODULE}.IBKRFlexClient") as mock_client,
        patch(f"{STAGED_MODULE}.IBKRParser") as mock_parser,
        patch(f"{STAGED_MODULE}.reconstruct_and_update_holdings") as mock_reconstruct,
        patch(f"{STAGED_MODULE}.merge_staging_to_production", return_value={}),
        patch(f"{STAGED_MODULE}.cleanup_staging"),
    ):
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

        mock_reconstruct.return_value = {}

        yield {
            "db": mock_db,
            "client": mock_client,
            "parser": mock_parser,
            "reconstruct": mock_reconstruct,
        }


def _run_staged_import(mocks, **overrides):
    """Call import_with_staging with _import_to_staging patched out, allowing per-test overrides."""
    from app.services.shared.staged_import_service import StagedImportService

    kwargs = {
        "db": mocks["db"],
        "account_id": 1,
        "flex_token": "tok",
        "flex_query_id": "qid",
        **overrides,
    }

    with patch.object(StagedImportService, "_import_to_staging") as mock_staging:
        mock_staging.return_value = {
            "positions": {},
            "transactions": {},
            "dividends": {},
            "transfers": {},
            "forex": {},
            "cash": {},
        }
        stats = StagedImportService.import_with_staging(**kwargs)

    return stats, mock_staging


class TestStagedImportWithTransactions:
    """Tests for StagedImportService passing transaction data."""

    def test_staged_import_extracts_transactions(self, staged_import_mocks):
        """Staged import should extract and pass transactions to _import_to_staging."""
        mock_parser = staged_import_mocks["parser"]
        mock_parser.extract_cash_balances.return_value = ["cash1"]
        mock_parser.extract_transactions.return_value = ["txn1", "txn2"]
        mock_parser.extract_dividends.return_value = ["div1"]
        mock_parser.extract_forex_transactions.return_value = ["fx1"]

        _stats, mock_staging = _run_staged_import(staged_import_mocks)

        kwargs = mock_staging.call_args.kwargs
        assert kwargs["transactions_data"] == ["txn1", "txn2"]
        assert kwargs["dividends_data"] == ["div1"]
        assert kwargs["forex_data"] == ["fx1"]

    def test_staged_import_calls_reconstruction_after_merge(self, staged_import_mocks):
        """Staged import should reconstruct holdings after merging staging to production."""
        staged_import_mocks["reconstruct"].return_value = {"holdings_updated": 5}

        stats, _mock_staging = _run_staged_import(staged_import_mocks)

        staged_import_mocks["reconstruct"].assert_called_once_with(staged_import_mocks["db"], 1)
        assert stats["holdings_reconstruction"] == {"holdings_updated": 5}
