"""Tests for PortfolioValuationService."""

from decimal import Decimal

from app.constants import AssetClass
from app.models import Asset
from app.services.portfolio.valuation_service import PortfolioValuationService


class TestValuationService:
    """Test PortfolioValuationService."""

    def test_calculate_day_change_cash(self, db):
        """Cash has no day change."""
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class=AssetClass.CASH,
            currency="USD",
        )
        db.add(cash_asset)
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_change(cash_asset, None)

        assert result.day_change is None
        assert result.is_market_closed is False

    def test_calculate_day_changes_batch_empty(self, db):
        """Empty asset list returns empty dict."""
        service = PortfolioValuationService(db)
        result = service.calculate_day_changes_batch([], {})
        assert result == {}

    def test_calculate_day_changes_batch_cash(self, db):
        """Cash assets in batch return no day change."""
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class=AssetClass.CASH,
            currency="USD",
        )
        db.add(cash_asset)
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_changes_batch([cash_asset], {cash_asset.id: None})

        assert cash_asset.id in result
        assert result[cash_asset.id].day_change is None
        assert result[cash_asset.id].is_market_closed is False

    def test_calculate_day_changes_batch_crypto(self, db):
        """Crypto assets are never market closed."""
        crypto_asset = Asset(
            symbol="BTC",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            currency="USD",
            last_fetched_price=Decimal("50000.00"),
        )
        db.add(crypto_asset)
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_changes_batch(
            [crypto_asset], {crypto_asset.id: Decimal("50000.00")}
        )

        assert crypto_asset.id in result
        assert result[crypto_asset.id].is_market_closed is False

    def test_service_initialization(self, db):
        """Service initializes correctly."""
        service = PortfolioValuationService(db)
        assert service._db == db
        assert service._price_repo is None  # Lazy loaded

    def test_price_repo_lazy_loading(self, db):
        """Price repo is lazy loaded on first access."""
        service = PortfolioValuationService(db)
        assert service._price_repo is None

        # Access the property
        repo = service.price_repo
        assert repo is not None
        assert service._price_repo is not None

        # Second access returns same instance
        assert service.price_repo is repo
