"""Integration tests for the synthetic snapshot import -> historical upload -> cleanup -> validation flow.

Tests the full lifecycle:
1. Synthetic snapshot creates BrokerDataSource + transactions + holdings
2. Synthetic cleanup deletes synthetic sources and returns snapshot_positions
3. Validation with matching data passes
4. Validation with discrepancies is detected
"""

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models import Account, Asset, BrokerDataSource, Holding, Portfolio, Transaction, User
from app.routers.broker_data import _delete_synthetic_sources
from app.services.auth.auth_service import AuthService
from app.services.brokers.ibkr.snapshot_validation_service import validate_against_snapshot
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService
from app.services.shared.asset_metadata_service import AssetMetadataResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_user(db):
    """Create a test user for the integration test."""
    user = User(
        email="synthetic-test@example.com",
        password_hash=AuthService.hash_password("testpassword123"),
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def test_portfolio(db, test_user):
    """Create a test portfolio linked to the test user."""
    portfolio = Portfolio(
        name="Synthetic Test Portfolio",
        user_id=str(test_user.id),
        default_currency="USD",
        is_default=True,
    )
    db.add(portfolio)
    db.flush()
    return portfolio


@pytest.fixture
def test_account(db, test_portfolio):
    """Create a test brokerage account linked to the portfolio with broker_type='ibkr'."""
    account = Account(
        name="IBKR Test Account",
        account_type="brokerage",
        institution="Interactive Brokers",
        currency="USD",
        broker_type="ibkr",
        is_active=True,
    )
    account.portfolios.append(test_portfolio)
    db.add(account)
    db.flush()
    return account


@pytest.fixture
def mock_positions_data():
    """IBKR positions data as returned by IBKRParser.extract_positions."""
    return [
        {
            "symbol": "AAPL",
            "original_symbol": "AAPL",
            "description": "Apple Inc.",
            "asset_class": "Equity",
            "currency": "USD",
            "quantity": Decimal("100"),
            "cost_basis": Decimal("15000"),
            "cusip": "037833100",
            "isin": "US0378331005",
            "conid": "265598",
            "figi": None,
        },
        {
            "symbol": "MSFT",
            "original_symbol": "MSFT",
            "description": "Microsoft Corp",
            "asset_class": "Equity",
            "currency": "USD",
            "quantity": Decimal("50"),
            "cost_basis": Decimal("20000"),
            "cusip": "594918104",
            "isin": "US5949181045",
            "conid": "272093",
            "figi": None,
        },
    ]


@pytest.fixture
def mock_cash_data():
    """IBKR cash balances as returned by IBKRParser.extract_cash_balances."""
    return [
        {
            "symbol": "USD",
            "currency": "USD",
            "balance": Decimal("5000.00"),
            "description": "United States Dollar",
            "asset_class": "Cash",
        },
    ]


@pytest.fixture
def mock_flex_xml():
    """Minimal valid XML bytes that IBKRFlexClient.fetch_flex_report would return."""
    return (
        b"<FlexQueryResponse><FlexStatements><FlexStatement /></FlexStatements></FlexQueryResponse>"
    )


@pytest.fixture
def mock_xml_root():
    """Parsed XML element that IBKRParser.parse_xml would return."""
    return ET.fromstring(
        b"<FlexQueryResponse><FlexStatements><FlexStatement /></FlexStatements></FlexQueryResponse>"
    )


# ---------------------------------------------------------------------------
# Test: Synthetic snapshot creates source, transactions, and holdings
# ---------------------------------------------------------------------------


class TestSyntheticSnapshotImport:
    """Tests for IBKRSyntheticImportService.import_snapshot."""

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.market_data.price_fetcher.PriceFetcher.fetch_price")
    @patch(
        "app.services.shared.asset_metadata_service.AssetMetadataService.fetch_name_from_yfinance"
    )
    def test_snapshot_creates_synthetic_source_and_transactions(
        self,
        mock_yfinance,
        mock_fetch_price,
        mock_parser,
        mock_flex_client,
        db,
        test_account,
        mock_positions_data,
        mock_cash_data,
        mock_flex_xml,
        mock_xml_root,
    ):
        """Importing a snapshot creates a synthetic BrokerDataSource, transactions, and holdings."""
        # Arrange: mock external APIs
        mock_flex_client.fetch_flex_report.return_value = mock_flex_xml
        mock_parser.parse_xml.return_value = mock_xml_root
        mock_parser.extract_positions.return_value = mock_positions_data
        mock_parser.extract_cash_balances.return_value = mock_cash_data
        mock_fetch_price.return_value = (Decimal("150.00"), None)
        mock_yfinance.return_value = AssetMetadataResult(
            symbol="", name=None, category=None, industry=None, source="not_found"
        )

        # Act
        result = IBKRSyntheticImportService.import_snapshot(
            db, test_account.id, flex_token="fake-token", flex_query_id="fake-query-id"
        )

        # Assert: import completed successfully
        assert result["status"] == "completed"
        assert result["positions_imported"] == 2

        # Assert: synthetic BrokerDataSource was created
        sources = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .all()
        )
        assert len(sources) == 1
        source = sources[0]
        assert source.broker_type == "ibkr"
        assert source.status == "completed"
        assert source.start_date == date.today()
        assert source.end_date == date.today()

        # Assert: snapshot_positions stored in import_stats
        snapshot_positions = source.import_stats["snapshot_positions"]
        assert len(snapshot_positions) == 2
        symbols = {p["symbol"] for p in snapshot_positions}
        assert symbols == {"AAPL", "MSFT"}

        # Assert: transactions exist linked to the synthetic source
        transactions = db.query(Transaction).filter(Transaction.broker_source_id == source.id).all()
        assert len(transactions) == 2

        # Check AAPL transaction
        aapl_txn = next(t for t in transactions if t.notes and "AAPL" in _get_holding_symbol(db, t))
        assert aapl_txn.type == "Buy"
        assert aapl_txn.quantity == Decimal("100")
        assert aapl_txn.price_per_unit == Decimal("150")  # 15000 / 100

        # Check MSFT transaction
        msft_txn = next(t for t in transactions if t.notes and "MSFT" in _get_holding_symbol(db, t))
        assert msft_txn.type == "Buy"
        assert msft_txn.quantity == Decimal("50")
        assert msft_txn.price_per_unit == Decimal("400")  # 20000 / 50

        # Assert: holdings were created for the account
        holdings = db.query(Holding).filter(Holding.account_id == test_account.id).all()
        # At least AAPL and MSFT (may also have USD cash holding)
        equity_holdings = [
            h
            for h in holdings
            if db.query(Asset).filter(Asset.id == h.asset_id).first().asset_class == "Equity"
        ]
        assert len(equity_holdings) == 2

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    def test_snapshot_fails_gracefully_on_api_error(
        self,
        mock_parser,
        mock_flex_client,
        db,
        test_account,
    ):
        """Snapshot import returns a failed status when the Flex API returns None."""
        mock_flex_client.fetch_flex_report.return_value = None

        result = IBKRSyntheticImportService.import_snapshot(
            db, test_account.id, flex_token="bad-token", flex_query_id="bad-query"
        )

        assert result["status"] == "failed"
        assert any("Failed to fetch" in e for e in result["errors"])

        # No synthetic source should be created
        source_count = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .count()
        )
        assert source_count == 0

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    def test_snapshot_fails_on_parse_error(
        self,
        mock_parser,
        mock_flex_client,
        db,
        test_account,
        mock_flex_xml,
    ):
        """Snapshot import returns failed when XML parsing fails."""
        mock_flex_client.fetch_flex_report.return_value = mock_flex_xml
        mock_parser.parse_xml.return_value = None

        result = IBKRSyntheticImportService.import_snapshot(
            db, test_account.id, flex_token="token", flex_query_id="query"
        )

        assert result["status"] == "failed"
        assert any("Failed to parse" in e for e in result["errors"])

    def test_snapshot_fails_for_nonexistent_account(self, db):
        """Snapshot import fails when account does not exist."""
        result = IBKRSyntheticImportService.import_snapshot(
            db, account_id=999999, flex_token="token", flex_query_id="query"
        )

        assert result["status"] == "failed"
        assert any("not found" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Test: Synthetic cleanup on historical upload
# ---------------------------------------------------------------------------


class TestSyntheticCleanup:
    """Tests for _delete_synthetic_sources function."""

    def test_delete_synthetic_sources_removes_source_and_transactions(self, db, test_account):
        """Deleting synthetic sources removes the source record and linked transactions."""
        # Arrange: create a synthetic source with a transaction
        source = BrokerDataSource(
            account_id=test_account.id,
            broker_type="ibkr",
            source_type="synthetic",
            source_identifier="Synthetic Snapshot 2026-02-07",
            start_date=date.today(),
            end_date=date.today(),
            status="completed",
            import_stats={
                "snapshot_positions": [
                    {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
                    {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
                ],
            },
        )
        db.add(source)
        db.flush()

        # Create a holding and transaction linked to the synthetic source
        asset = Asset(
            symbol="TEST-AAPL",
            name="Apple Inc. (Test)",
            asset_class="Equity",
            currency="USD",
        )
        db.add(asset)
        db.flush()

        holding = Holding(
            account_id=test_account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            cost_basis=Decimal("15000"),
            is_active=True,
        )
        db.add(holding)
        db.flush()

        txn = Transaction(
            holding_id=holding.id,
            broker_source_id=source.id,
            date=date.today(),
            type="Buy",
            quantity=Decimal("100"),
            price_per_unit=Decimal("150"),
            fees=Decimal("0"),
            notes="Synthetic transaction",
        )
        db.add(txn)
        db.flush()

        # Act
        result = _delete_synthetic_sources(db, test_account.id, "ibkr")

        # Assert: sources and transactions deleted
        assert result["deleted_sources"] == 1
        assert result["deleted_transactions"] == 1

        # Assert: snapshot_positions are returned for validation
        assert len(result["snapshot_positions"]) == 2
        assert result["snapshot_positions"][0]["symbol"] == "AAPL"

        # Assert: no synthetic sources remain in DB
        remaining = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .count()
        )
        assert remaining == 0

        # Assert: transaction was deleted
        remaining_txns = (
            db.query(Transaction).filter(Transaction.broker_source_id == source.id).count()
        )
        assert remaining_txns == 0

    def test_delete_synthetic_sources_returns_empty_when_none_exist(self, db, test_account):
        """Returns zero counts when no synthetic sources exist for the account."""
        result = _delete_synthetic_sources(db, test_account.id, "ibkr")

        assert result["deleted_sources"] == 0
        assert result["deleted_transactions"] == 0

    def test_delete_synthetic_sources_ignores_non_synthetic(self, db, test_account):
        """Non-synthetic sources (file_upload) are not deleted."""
        # Arrange: create a non-synthetic source
        source = BrokerDataSource(
            account_id=test_account.id,
            broker_type="ibkr",
            source_type="file_upload",
            source_identifier="my-upload.xml",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            status="completed",
        )
        db.add(source)
        db.flush()

        # Act
        result = _delete_synthetic_sources(db, test_account.id, "ibkr")

        # Assert: non-synthetic source is untouched
        assert result["deleted_sources"] == 0
        remaining = (
            db.query(BrokerDataSource)
            .filter(BrokerDataSource.account_id == test_account.id)
            .count()
        )
        assert remaining == 1

    def test_delete_synthetic_sources_scoped_to_broker_type(self, db, test_account):
        """Synthetic cleanup is scoped by broker_type."""
        # Arrange: create synthetic source for a different broker
        source = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="synthetic",
            source_identifier="Synthetic Kraken",
            start_date=date.today(),
            end_date=date.today(),
            status="completed",
        )
        db.add(source)
        db.flush()

        # Act: clean up ibkr (not kraken)
        result = _delete_synthetic_sources(db, test_account.id, "ibkr")

        # Assert: kraken source is untouched
        assert result["deleted_sources"] == 0
        remaining = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .count()
        )
        assert remaining == 1


# ---------------------------------------------------------------------------
# Test: Validation with matching data
# ---------------------------------------------------------------------------


class TestSnapshotValidationMatching:
    """Tests for validate_against_snapshot with matching data."""

    def test_validation_passes_with_exact_match(self):
        """Validation passes when reconstructed holdings match snapshot exactly."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
        ]
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
            {"symbol": "MSFT", "quantity": Decimal("50"), "cost_basis": Decimal("20000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is True
        assert result["discrepancies"] == []
        assert result["positions_checked"] == 2
        assert result["positions_matched"] == 2

    def test_validation_passes_with_cost_basis_within_tolerance(self):
        """Cost basis differences within 2% tolerance are acceptable."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        # 1% difference in cost basis (15150 vs 15000 = 1%)
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15150")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is True
        assert result["positions_checked"] == 1
        assert result["positions_matched"] == 1

    def test_validation_passes_ignoring_zero_quantity_snapshot(self):
        """Zero-quantity positions in the snapshot are skipped."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "CLOSED", "quantity": "0", "cost_basis": "0", "currency": "USD"},
        ]
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is True
        # Only 1 non-zero position checked
        assert result["positions_checked"] == 1
        assert result["positions_matched"] == 1

    def test_validation_passes_with_extra_reconstructed_holdings(self):
        """Extra holdings in reconstruction (closed positions) do not invalidate."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
            {"symbol": "GOOG", "quantity": Decimal("25"), "cost_basis": Decimal("5000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is True
        assert result["positions_checked"] == 1


# ---------------------------------------------------------------------------
# Test: Validation with discrepancies
# ---------------------------------------------------------------------------


class TestSnapshotValidationDiscrepancies:
    """Tests for validate_against_snapshot with mismatches."""

    def test_validation_fails_with_missing_position(self):
        """A position in the snapshot but missing from reconstructed holdings is flagged."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
        ]
        # Only AAPL present, MSFT missing
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is False
        assert result["positions_checked"] == 2
        assert result["positions_matched"] == 1
        assert len(result["discrepancies"]) == 1

        disc = result["discrepancies"][0]
        assert disc["type"] == "missing_position"
        assert disc["symbol"] == "MSFT"
        assert disc["expected_quantity"] == "50"

    def test_validation_fails_with_quantity_mismatch(self):
        """Quantity mismatch between snapshot and reconstruction is flagged."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("80"), "cost_basis": Decimal("12000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is False
        assert len(result["discrepancies"]) == 1

        disc = result["discrepancies"][0]
        assert disc["type"] == "quantity_mismatch"
        assert disc["symbol"] == "AAPL"
        assert disc["expected_quantity"] == "100"
        assert disc["actual_quantity"] == "80"

    def test_validation_reports_cost_basis_mismatch_but_stays_valid(self):
        """Cost basis beyond 2% tolerance is reported but does not invalidate."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        # 5% cost basis difference (15750 vs 15000 = 5%)
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15750")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        # cost_basis_mismatch alone does NOT invalidate
        assert result["is_valid"] is True
        assert result["positions_matched"] == 1
        assert len(result["discrepancies"]) == 1

        disc = result["discrepancies"][0]
        assert disc["type"] == "cost_basis_mismatch"
        assert disc["symbol"] == "AAPL"

    def test_validation_with_all_positions_missing(self):
        """All positions missing from reconstruction."""
        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
        ]
        reconstructed_holdings = []

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is False
        assert result["positions_checked"] == 2
        assert result["positions_matched"] == 0
        assert len(result["discrepancies"]) == 2

    def test_validation_with_empty_snapshot(self):
        """Empty snapshot means nothing to validate -- passes."""
        snapshot_positions = []
        reconstructed_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = validate_against_snapshot(snapshot_positions, reconstructed_holdings)

        assert result["is_valid"] is True
        assert result["positions_checked"] == 0
        assert result["positions_matched"] == 0


# ---------------------------------------------------------------------------
# Test: Full end-to-end flow
# ---------------------------------------------------------------------------


class TestFullSyntheticToHistoryFlow:
    """End-to-end test: snapshot -> cleanup -> validation."""

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.market_data.price_fetcher.PriceFetcher.fetch_price")
    @patch(
        "app.services.shared.asset_metadata_service.AssetMetadataService.fetch_name_from_yfinance"
    )
    def test_full_flow_snapshot_cleanup_and_validation(
        self,
        mock_yfinance,
        mock_fetch_price,
        mock_parser,
        mock_flex_client,
        db,
        test_account,
        mock_positions_data,
        mock_cash_data,
        mock_flex_xml,
        mock_xml_root,
    ):
        """Full flow: import snapshot, clean up synthetic sources, validate holdings."""
        # -- Step 1: Import synthetic snapshot --
        mock_flex_client.fetch_flex_report.return_value = mock_flex_xml
        mock_parser.parse_xml.return_value = mock_xml_root
        mock_parser.extract_positions.return_value = mock_positions_data
        mock_parser.extract_cash_balances.return_value = mock_cash_data
        mock_fetch_price.return_value = (Decimal("150.00"), None)
        mock_yfinance.return_value = AssetMetadataResult(
            symbol="", name=None, category=None, industry=None, source="not_found"
        )

        import_result = IBKRSyntheticImportService.import_snapshot(
            db, test_account.id, flex_token="token", flex_query_id="query"
        )
        assert import_result["status"] == "completed"

        # Verify synthetic source exists
        synthetic_source = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .first()
        )
        assert synthetic_source is not None
        assert len(synthetic_source.import_stats["snapshot_positions"]) == 2

        # -- Step 2: Clean up synthetic sources (simulates historical upload) --
        cleanup_result = _delete_synthetic_sources(db, test_account.id, "ibkr")

        assert cleanup_result["deleted_sources"] == 1
        assert cleanup_result["deleted_transactions"] == 2
        assert len(cleanup_result["snapshot_positions"]) == 2

        # Verify synthetic source is gone
        remaining = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == test_account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .count()
        )
        assert remaining == 0

        # -- Step 3: Validate with matching data --
        # Simulate what finalize_batch_upload does: compare snapshot vs reconstructed
        matching_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
            {"symbol": "MSFT", "quantity": Decimal("50"), "cost_basis": Decimal("20000")},
        ]
        validation_result = validate_against_snapshot(
            cleanup_result["snapshot_positions"], matching_holdings
        )

        assert validation_result["is_valid"] is True
        assert validation_result["positions_checked"] == 2
        assert validation_result["positions_matched"] == 2
        assert validation_result["discrepancies"] == []

        # -- Step 4: Validate with partial data (missing MSFT) --
        partial_holdings = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]
        partial_validation = validate_against_snapshot(
            cleanup_result["snapshot_positions"], partial_holdings
        )

        assert partial_validation["is_valid"] is False
        assert partial_validation["positions_matched"] == 1
        assert len(partial_validation["discrepancies"]) == 1
        assert partial_validation["discrepancies"][0]["type"] == "missing_position"
        assert partial_validation["discrepancies"][0]["symbol"] == "MSFT"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_holding_symbol(db, transaction: Transaction) -> str:
    """Get the asset symbol for a transaction by looking up its holding."""
    holding = db.query(Holding).filter(Holding.id == transaction.holding_id).first()
    if not holding:
        return ""
    asset = db.query(Asset).filter(Asset.id == holding.asset_id).first()
    return asset.symbol if asset else ""
