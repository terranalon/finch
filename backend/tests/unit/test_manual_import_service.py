"""Tests for Manual Import service."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models import Asset, Holding
from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)
from app.services.brokers.manual.import_service import ManualImportService
from app.services.shared.transaction_hash_service import DedupResult


def _create_service() -> ManualImportService:
    """Create a ManualImportService with mocked DB and repositories."""
    db = MagicMock(spec=Session)
    service = ManualImportService(db, "manual")
    service._asset_repo = MagicMock()
    service._holding_repo = MagicMock()
    return service


def _setup_asset_holding(
    service: ManualImportService,
    asset_id: int = 1,
    symbol: str = "AAPL",
    holding_id: int = 10,
    *,
    use_find_by_symbol: bool = True,
) -> tuple[MagicMock, MagicMock]:
    """Wire up mocked asset and holding on a service instance.

    When use_find_by_symbol is True, the asset is returned by find_by_symbol (existing asset).
    When False, the asset is returned by find_or_create (new asset via cash path).
    """
    mock_asset = MagicMock(spec=Asset, id=asset_id, symbol=symbol)
    mock_holding = MagicMock(spec=Holding, id=holding_id)

    if use_find_by_symbol:
        service._asset_repo.find_by_symbol.return_value = mock_asset
    else:
        service._asset_repo.find_or_create.return_value = (mock_asset, False)

    service._holding_repo.find_or_create.return_value = (mock_holding, False)
    return mock_asset, mock_holding


class TestManualImportServiceMetadata:
    def test_supported_broker_types(self):
        assert ManualImportService.supported_broker_types() == ["manual"]


class TestManualImportBuySell:
    @patch("app.services.brokers.manual.import_service.create_or_transfer_transaction")
    def test_import_buy_transaction(self, mock_create_txn):
        service = _create_service()
        _setup_asset_holding(service)
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

        data = BrokerImportData(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
            transactions=[
                ParsedTransaction(
                    trade_date=date(2025, 1, 15),
                    symbol="AAPL",
                    transaction_type="Buy",
                    quantity=Decimal("10"),
                    price_per_unit=Decimal("175.50"),
                    amount=Decimal("1755.00"),
                    currency="USD",
                    fees=Decimal("4.99"),
                ),
            ],
        )

        stats = service.import_data(1, data, source_id=100, skip_reconstruction=True)

        assert stats["status"] == "completed"
        assert stats["transactions"]["imported"] == 1
        mock_create_txn.assert_called_once()


class TestManualImportCash:
    @patch("app.services.brokers.manual.import_service.create_or_transfer_transaction")
    def test_import_deposit(self, mock_create_txn):
        service = _create_service()
        _setup_asset_holding(
            service, asset_id=2, symbol="USD", holding_id=20, use_find_by_symbol=False
        )
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

        data = BrokerImportData(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 1),
            cash_transactions=[
                ParsedCashTransaction(
                    date=date(2025, 2, 1),
                    transaction_type="Deposit",
                    amount=Decimal("10000.00"),
                    currency="USD",
                ),
            ],
        )

        stats = service.import_data(1, data, source_id=100, skip_reconstruction=True)

        assert stats["status"] == "completed"
        assert stats["cash_transactions"]["imported"] == 1


class TestManualImportDividends:
    @patch("app.services.brokers.manual.import_service.create_or_transfer_transaction")
    def test_import_dividend(self, mock_create_txn):
        service = _create_service()
        _setup_asset_holding(service, asset_id=3, holding_id=30)
        mock_create_txn.return_value = (DedupResult.NEW, MagicMock())

        data = BrokerImportData(
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 1),
            dividends=[
                ParsedTransaction(
                    trade_date=date(2025, 4, 1),
                    symbol="AAPL",
                    transaction_type="Dividend",
                    amount=Decimal("9.50"),
                    currency="USD",
                ),
            ],
        )

        stats = service.import_data(1, data, source_id=100, skip_reconstruction=True)

        assert stats["status"] == "completed"
        assert stats["dividends"]["imported"] == 1


class TestManualAssetResolution:
    def test_existing_asset_returns_from_db(self):
        service = _create_service()
        mock_asset = MagicMock(spec=Asset, id=1, symbol="AAPL")
        service._asset_repo.find_by_symbol.return_value = mock_asset

        asset, created = service._find_or_create_asset("AAPL", "USD")
        assert asset == mock_asset
        assert created is False

    @patch("app.services.brokers.manual.import_service.ManualImportService._try_coingecko")
    @patch("app.services.brokers.manual.import_service.ManualImportService._try_yfinance")
    def test_yfinance_detected_stock(self, mock_yf, mock_cg):
        service = _create_service()
        service._asset_repo.find_by_symbol.return_value = None

        mock_yf.return_value = ("Stock", "Apple Inc.", "Technology", "Consumer Electronics")
        mock_new_asset = MagicMock(spec=Asset, id=5)
        service._asset_repo.find_or_create.return_value = (mock_new_asset, True)

        asset, created = service._find_or_create_asset("AAPL", "USD")
        assert created is True
        service._asset_repo.find_or_create.assert_called_once_with(
            "AAPL",
            name="Apple Inc.",
            asset_class="Stock",
            currency="USD",
            category="Technology",
            industry="Consumer Electronics",
            data_source="manual",
        )

    @patch("app.services.brokers.manual.import_service.ManualImportService._try_coingecko")
    @patch("app.services.brokers.manual.import_service.ManualImportService._try_yfinance")
    def test_coingecko_detected_crypto(self, mock_yf, mock_cg):
        service = _create_service()
        service._asset_repo.find_by_symbol.return_value = None

        mock_yf.return_value = (None, None, None, None)
        mock_cg.return_value = "Bitcoin"
        mock_new_asset = MagicMock(spec=Asset, id=6)
        service._asset_repo.find_or_create.return_value = (mock_new_asset, True)

        asset, created = service._find_or_create_asset("BTC", "USD")
        assert created is True
        service._asset_repo.find_or_create.assert_called_once_with(
            "BTC",
            name="Bitcoin",
            asset_class="Crypto",
            currency="USD",
            category="Cryptocurrency",
            data_source="manual",
        )

    @patch("app.services.brokers.manual.import_service.ManualImportService._try_coingecko")
    @patch("app.services.brokers.manual.import_service.ManualImportService._try_yfinance")
    def test_fallback_to_stock(self, mock_yf, mock_cg):
        service = _create_service()
        service._asset_repo.find_by_symbol.return_value = None

        mock_yf.return_value = (None, None, None, None)
        mock_cg.return_value = None
        mock_new_asset = MagicMock(spec=Asset, id=7)
        service._asset_repo.find_or_create.return_value = (mock_new_asset, True)

        asset, created = service._find_or_create_asset("UNKNOWN", "USD")
        assert created is True
        service._asset_repo.find_or_create.assert_called_once_with(
            "UNKNOWN",
            name="UNKNOWN",
            asset_class="Stock",
            currency="USD",
            data_source="manual",
        )
