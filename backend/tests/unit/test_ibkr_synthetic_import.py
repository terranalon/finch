"""Tests for IBKR synthetic snapshot import service."""

from dataclasses import replace
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import Account
from app.models.daily_cash_balance import DailyCashBalance
from app.services.brokers.ibkr.models import IBKRCashBalance, IBKRPosition
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService
from app.services.shared.transaction_hash_service import DedupResult

AAPL_POSITION = IBKRPosition(
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
    cusip="037833100",
    isin="US0378331005",
    conid="265598",
    figi=None,
)

MSFT_POSITION = IBKRPosition(
    symbol="MSFT",
    original_symbol="MSFT",
    description="MICROSOFT CORP",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="NASDAQ",
    quantity=Decimal("50"),
    cost_basis=Decimal("20000"),
    currency="USD",
    account_id="U12345",
    needs_validation=False,
)

USD_CASH_BALANCE = IBKRCashBalance(
    symbol="USD",
    currency="USD",
    balance=Decimal("5000"),
    description="US Dollar",
    asset_class="Cash",
    account_id="U12345",
)

EUR_CASH_BALANCE = IBKRCashBalance(
    symbol="EUR",
    currency="EUR",
    balance=Decimal("500"),
    description="Euro",
    asset_class="Cash",
    account_id="U12345",
)

BMW_POSITION = IBKRPosition(
    symbol="BMW.DE",
    original_symbol="BMW",
    description="BMW AG",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="IBIS",
    quantity=Decimal("10"),
    cost_basis=Decimal("5000"),
    currency="EUR",
    account_id="U12345",
    needs_validation=False,
)


def _find_added_synthetic_source(mock_db: MagicMock) -> object | None:
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

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_synthetic_source(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """import_snapshot should create a BrokerDataSource with source_type='synthetic'."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [AAPL_POSITION]
        mock_parser.extract_cash_balances.return_value = [USD_CASH_BALANCE]

        mock_import_service._import_cash_balances.return_value = {"holdings_created": 1}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "completed"
        assert stats["source_type"] == "synthetic"

        source_added = _find_added_synthetic_source(mock_db_with_account)
        assert source_added is not None
        assert source_added.source_type == "synthetic"

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_buy_transactions_from_positions(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """Each position should generate a synthetic Buy transaction."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [AAPL_POSITION, MSFT_POSITION]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 2}
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["positions_imported"] == 2

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_stores_snapshot_data_for_validation(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """Snapshot data should be stored in import_stats for later validation."""
        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = [replace(AAPL_POSITION, isin=None, conid=None)]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

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


def _added_objects(mock_db: MagicMock) -> list:
    """Extract all objects passed to mock_db.add() calls."""
    return [call[0][0] for call in mock_db.add.call_args_list]


def _deposit_calls(mock_create_txn: MagicMock) -> list:
    """Filter create_or_transfer_transaction calls to Deposit type only."""
    return [c for c in mock_create_txn.call_args_list if c.kwargs.get("txn_type") == "Deposit"]


def _setup_snapshot_mocks(
    mock_client: MagicMock,
    mock_parser: MagicMock,
    mock_import_service: MagicMock,
    mock_reconstruct: MagicMock,
    mock_create_txn: MagicMock,
    *,
    positions: list[IBKRPosition],
    cash_balances: list[IBKRCashBalance],
) -> None:
    """Wire up the standard mock chain for import_snapshot tests."""
    mock_client.fetch_flex_report.return_value = b"<xml/>"
    mock_parser.parse_xml.return_value = MagicMock()
    mock_parser.extract_positions.return_value = positions
    mock_parser.extract_cash_balances.return_value = cash_balances
    mock_import_service._import_cash_balances.return_value = {}
    mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
    mock_reconstruct.return_value = {"holdings_updated": len(positions)}
    mock_create_txn.return_value = (DedupResult.NEW, MagicMock())


class TestSyntheticDepositInflation:
    """Tests for inflated deposits, Trade Settlements, and DailyCashBalance."""

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_deposit_inflated_by_position_cost_basis(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """Deposit amount should be cash balance + total cost basis for that currency."""
        _setup_snapshot_mocks(
            mock_client,
            mock_parser,
            mock_import_service,
            mock_reconstruct,
            mock_create_txn,
            positions=[AAPL_POSITION, MSFT_POSITION],
            cash_balances=[USD_CASH_BALANCE],
        )

        IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="t", flex_query_id="q"
        )

        # amount should be 5000 (cash) + 15000 + 20000 = 40000
        deposits = _deposit_calls(mock_create_txn)
        assert len(deposits) == 1
        assert deposits[0].kwargs["amount"] == Decimal("40000")
        assert deposits[0].kwargs["quantity"] == Decimal("40000")

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_trade_settlements_created_for_each_buy(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """Each Buy should have a matching Trade Settlement with negative cost basis."""
        _setup_snapshot_mocks(
            mock_client,
            mock_parser,
            mock_import_service,
            mock_reconstruct,
            mock_create_txn,
            positions=[AAPL_POSITION, MSFT_POSITION],
            cash_balances=[USD_CASH_BALANCE],
        )

        IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="t", flex_query_id="q"
        )

        settlements = [
            obj
            for obj in _added_objects(mock_db_with_account)
            if hasattr(obj, "type") and obj.type == "Trade Settlement"
        ]
        assert len(settlements) == 2
        settlement_amounts = sorted(s.amount for s in settlements)
        assert settlement_amounts == [Decimal("-20000"), Decimal("-15000")]

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_daily_cash_balance_created(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """A DailyCashBalance record should be created for the actual cash balance."""
        _setup_snapshot_mocks(
            mock_client,
            mock_parser,
            mock_import_service,
            mock_reconstruct,
            mock_create_txn,
            positions=[AAPL_POSITION],
            cash_balances=[USD_CASH_BALANCE],
        )

        IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="t", flex_query_id="q"
        )

        cash_balances = [
            obj for obj in _added_objects(mock_db_with_account) if isinstance(obj, DailyCashBalance)
        ]
        assert len(cash_balances) == 1
        assert cash_balances[0].currency == "USD"
        assert cash_balances[0].balance == Decimal("5000")

    @patch("app.services.brokers.ibkr.synthetic_import_service.create_or_transfer_transaction")
    @patch("app.services.brokers.ibkr.synthetic_import_service.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_deposit_created_for_currency_with_no_cash_entry(
        self,
        mock_client,
        mock_parser,
        mock_import_service,
        mock_reconstruct,
        mock_create_txn,
        mock_db_with_account,
    ):
        """Positions in a currency with no cash entry should still get a deposit."""
        _setup_snapshot_mocks(
            mock_client,
            mock_parser,
            mock_import_service,
            mock_reconstruct,
            mock_create_txn,
            positions=[AAPL_POSITION, BMW_POSITION],
            cash_balances=[USD_CASH_BALANCE],
        )

        IBKRSyntheticImportService.import_snapshot(
            mock_db_with_account, account_id=1, flex_token="t", flex_query_id="q"
        )

        # USD (5000+15000=20000) and EUR (0+5000=5000)
        deposits = _deposit_calls(mock_create_txn)
        assert len(deposits) == 2
        deposit_amounts = sorted(c.kwargs["amount"] for c in deposits)
        assert deposit_amounts == [Decimal("5000"), Decimal("20000")]
