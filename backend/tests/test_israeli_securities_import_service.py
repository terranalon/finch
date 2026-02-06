"""Tests for Israeli Securities Import Service."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)
from app.services.brokers.shared.israeli_import_service import IsraeliSecuritiesImportService


class TestSymbolResolution:
    """Test symbol resolution from TASE security numbers."""

    def test_resolve_tase_symbol_found(self):
        """Test resolving TASE symbol when found in cache."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock TASE service lookup
        with patch.object(service.tase_service, "get_yahoo_symbol", return_value="TEVA.TA"):
            symbol, tase_number = service._resolve_symbol("TASE:1234567")

        assert symbol == "TEVA.TA"
        assert tase_number == "1234567"

    def test_resolve_tase_symbol_not_found(self):
        """Test resolving TASE symbol when not found in cache."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock TASE service lookup returning None
        with patch.object(service.tase_service, "get_yahoo_symbol", return_value=None):
            symbol, tase_number = service._resolve_symbol("TASE:9999999")

        assert symbol is None
        assert tase_number == "9999999"

    def test_resolve_non_tase_symbol(self):
        """Test resolving non-TASE symbol returns as-is."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        symbol, tase_number = service._resolve_symbol("AAPL")

        assert symbol == "AAPL"
        assert tase_number is None


class TestFindOrCreateAsset:
    """Test asset creation and lookup."""

    def test_find_existing_asset_by_symbol(self):
        """Test finding existing asset by symbol."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock existing asset
        mock_asset = MagicMock()
        mock_asset.tase_security_number = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset

        asset, created = service._find_or_create_asset(
            symbol="TEVA.TA",
            name="Teva",
            asset_class="Stock",
            currency="ILS",
            tase_security_number="1234567",
        )

        assert asset == mock_asset
        assert created is False
        # Should update TASE number since it was missing
        assert mock_asset.tase_security_number == "1234567"

    def test_find_existing_asset_by_tase_number(self):
        """Test finding existing asset by TASE security number."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # First query (by symbol) returns None
        # Second query (by TASE number) returns asset
        mock_asset = MagicMock()
        mock_asset.symbol = "TASE:1234567"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # Not found by symbol
            mock_asset,  # Found by TASE number
        ]

        asset, created = service._find_or_create_asset(
            symbol="TEVA.TA",
            name="Teva",
            asset_class="Stock",
            currency="ILS",
            tase_security_number="1234567",
        )

        assert asset == mock_asset
        assert created is False
        # Should update symbol from placeholder to resolved
        assert mock_asset.symbol == "TEVA.TA"

    def test_create_new_asset(self):
        """Test creating new asset when not found."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Both queries return None (asset not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        asset, created = service._find_or_create_asset(
            symbol="TEVA.TA",
            name="Teva",
            asset_class="Stock",
            currency="ILS",
            tase_security_number="1234567",
        )

        assert created is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_create_cash_asset_with_price_1(self):
        """Test creating cash asset sets price to 1."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Asset not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        asset, created = service._find_or_create_asset(
            symbol="ILS",
            name="ILS Cash",
            asset_class="Cash",
            currency="ILS",
        )

        assert created is True
        # Verify the asset was added
        call_args = mock_db.add.call_args[0][0]
        assert call_args.last_fetched_price == Decimal("1")


class TestImportTransactions:
    """Test transaction import."""

    def test_import_transactions(self):
        """Test importing buy/sell transactions."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock queries
        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_holding = MagicMock()
        mock_holding.id = 1

        # First call: asset lookup, second: holding lookup, third: duplicate check
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_asset,  # Asset found
            mock_holding,  # Holding found
            None,  # No duplicate
        ]

        transactions = [
            ParsedTransaction(
                trade_date=date(2024, 1, 15),
                symbol="TEVA.TA",
                transaction_type="Buy",
                quantity=Decimal("50"),
                price_per_unit=Decimal("150"),
                amount=Decimal("7500"),
                fees=Decimal("25"),
                currency="ILS",
            ),
        ]

        with patch.object(service, "_resolve_symbol", return_value=("TEVA.TA", None)):
            stats = service._import_transactions(account_id=1, transactions=transactions)

        assert stats["total"] == 1
        assert stats["imported"] == 1

    def test_import_transactions_skips_duplicates(self):
        """Test that duplicate transactions are skipped via hash-based dedup."""
        from app.services.shared.transaction_hash_service import DedupResult

        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock queries
        mock_asset = MagicMock()
        mock_holding = MagicMock()

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_asset,
            mock_holding,
        ]

        transactions = [
            ParsedTransaction(
                trade_date=date(2024, 1, 15),
                symbol="TEVA.TA",
                transaction_type="Buy",
                quantity=Decimal("50"),
                price_per_unit=Decimal("150"),
                amount=Decimal("7500"),
                fees=Decimal("25"),
                currency="ILS",
            ),
        ]

        # Mock both symbol resolution and the hash-based dedup to return SKIPPED
        with (
            patch.object(service, "_resolve_symbol", return_value=("TEVA.TA", None)),
            patch(
                "app.services.brokers.shared.israeli_import_service.check_and_transfer_ownership",
                return_value=(DedupResult.SKIPPED, MagicMock()),
            ),
        ):
            stats = service._import_transactions(account_id=1, transactions=transactions)

        # Hash-based dedup uses "skipped" key
        assert stats["skipped"] == 1
        assert stats["imported"] == 0


class TestImportCashTransactions:
    """Test cash transaction import."""

    def test_import_deposit(self):
        """Test importing deposit transaction."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Mock: asset not found (create), holding not found (create), no duplicate
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # Cash asset not found
            None,  # Another query for TASE number
            None,  # Holding not found
            None,  # No duplicate
        ]

        cash_transactions = [
            ParsedCashTransaction(
                date=date(2024, 1, 15),
                transaction_type="Deposit",
                amount=Decimal("10000"),
                currency="ILS",
            ),
        ]

        stats = service._import_cash_transactions(account_id=1, cash_transactions=cash_transactions)

        assert stats["total"] == 1
        assert stats["imported"] == 1


class TestImportDividends:
    """Test dividend import."""

    def test_import_dividends(self):
        """Test importing dividend transactions."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        mock_asset = MagicMock()
        mock_holding = MagicMock()

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_asset,
            mock_holding,
            None,  # No duplicate
        ]

        dividends = [
            ParsedTransaction(
                trade_date=date(2024, 1, 15),
                symbol="TEVA.TA",
                transaction_type="Dividend",
                amount=Decimal("150"),
                currency="ILS",
            ),
        ]

        with patch.object(service, "_resolve_symbol", return_value=("TEVA.TA", None)):
            stats = service._import_dividends(account_id=1, dividends=dividends)

        assert stats["total"] == 1
        assert stats["imported"] == 1


class TestImportData:
    """Test full data import."""

    def test_import_data_success(self):
        """Test successful full data import."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        data = BrokerImportData(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            positions=[],
            transactions=[],
            cash_transactions=[],
            dividends=[],
        )

        stats = service.import_data(account_id=1, data=data)

        assert stats["status"] == "completed"
        mock_db.commit.assert_called_once()

    def test_import_data_rollback_on_error(self):
        """Test rollback on import failure."""
        mock_db = MagicMock()
        service = IsraeliSecuritiesImportService(mock_db, "meitav")

        # Make _import_transactions raise an error
        with patch.object(service, "_import_transactions", side_effect=Exception("Test error")):
            data = BrokerImportData(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                transactions=[
                    ParsedTransaction(
                        trade_date=date(2024, 1, 15),
                        symbol="TEST",
                        transaction_type="Buy",
                        quantity=Decimal("100"),
                        price_per_unit=Decimal("10"),
                        currency="ILS",
                    )
                ],
            )

            stats = service.import_data(account_id=1, data=data)

        assert stats["status"] == "failed"
        assert "Test error" in stats["errors"][0]
        mock_db.rollback.assert_called_once()
