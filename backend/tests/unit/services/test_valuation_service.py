"""Tests for PortfolioValuationService."""

from datetime import date, timedelta
from decimal import Decimal

from app.constants import AssetClass
from app.models import Asset, AssetPrice
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

    def test_day_change_filters_out_todays_prices(self, db):
        """Day change uses yesterday's close, not today's, to avoid race condition.

        This prevents incorrect day change when today's close is recorded
        while we're calculating (e.g., by a background price update job).
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        crypto_asset = Asset(
            symbol="BTC",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            currency="USD",
            last_fetched_price=Decimal("52000.00"),  # Current live price
        )
        db.add(crypto_asset)
        db.flush()

        # Yesterday's close (this should be used as previous_close)
        yesterday_price = AssetPrice(
            asset_id=crypto_asset.id,
            date=yesterday,
            closing_price=Decimal("50000.00"),
            currency="USD",
        )
        # Today's close already recorded (simulating race condition)
        today_price = AssetPrice(
            asset_id=crypto_asset.id,
            date=today,
            closing_price=Decimal("51500.00"),
            currency="USD",
        )
        db.add_all([yesterday_price, today_price])
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_change(
            crypto_asset,
            current_price=Decimal("52000.00"),
            today=today,
        )

        # Should compare 52000 (current) vs 50000 (yesterday), NOT 51500 (today)
        assert result.previous_close_price == Decimal("50000.00")
        assert result.day_change == Decimal("2000.00")
        assert result.day_change_pct == Decimal("4.00")

    def test_day_change_batch_filters_out_todays_prices(self, db):
        """Batch day change also filters out today's prices."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        crypto_asset = Asset(
            symbol="ETH",
            name="Ethereum",
            asset_class=AssetClass.CRYPTO,
            currency="USD",
            last_fetched_price=Decimal("3200.00"),
        )
        db.add(crypto_asset)
        db.flush()

        yesterday_price = AssetPrice(
            asset_id=crypto_asset.id,
            date=yesterday,
            closing_price=Decimal("3000.00"),
            currency="USD",
        )
        today_price = AssetPrice(
            asset_id=crypto_asset.id,
            date=today,
            closing_price=Decimal("3100.00"),
            currency="USD",
        )
        db.add_all([yesterday_price, today_price])
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_changes_batch(
            [crypto_asset],
            {crypto_asset.id: Decimal("3200.00")},
            today=today,
        )

        # Should compare 3200 (current) vs 3000 (yesterday), NOT 3100 (today)
        assert result[crypto_asset.id].previous_close_price == Decimal("3000.00")
        assert result[crypto_asset.id].day_change == Decimal("200.00")
