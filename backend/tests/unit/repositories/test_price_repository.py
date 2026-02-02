"""Tests for PriceRepository."""

from datetime import date, timedelta
from decimal import Decimal

from app.models import AssetPrice
from app.services.repositories.price_repository import PriceRepository


class TestPriceRepository:
    """Test cases for PriceRepository."""

    def test_find_latest_by_asset(self, db, test_asset):
        """Can find the most recent price for an asset."""
        price = AssetPrice(
            asset_id=test_asset.id,
            date=date.today(),
            closing_price=Decimal("150.00"),
            currency="USD",
        )
        db.add(price)
        db.commit()

        repo = PriceRepository(db)
        latest = repo.find_latest_by_asset(test_asset.id)
        assert latest is not None
        assert latest.closing_price == Decimal("150.00")

    def test_find_latest_by_asset_returns_most_recent(self, db, test_asset):
        """Returns the most recent price when multiple exist."""
        today = date.today()
        old_price = AssetPrice(
            asset_id=test_asset.id,
            date=today - timedelta(days=5),
            closing_price=Decimal("140.00"),
            currency="USD",
        )
        new_price = AssetPrice(
            asset_id=test_asset.id,
            date=today,
            closing_price=Decimal("150.00"),
            currency="USD",
        )
        db.add_all([old_price, new_price])
        db.commit()

        repo = PriceRepository(db)
        latest = repo.find_latest_by_asset(test_asset.id)
        assert latest is not None
        assert latest.closing_price == Decimal("150.00")
        assert latest.date == today

    def test_find_latest_by_asset_returns_none_if_no_prices(self, db, test_asset):
        """Returns None if no prices exist for asset."""
        repo = PriceRepository(db)
        latest = repo.find_latest_by_asset(test_asset.id)
        assert latest is None

    def test_find_by_asset_and_date(self, db, test_asset):
        """Can find price for specific date."""
        target_date = date.today() - timedelta(days=5)
        price = AssetPrice(
            asset_id=test_asset.id,
            date=target_date,
            closing_price=Decimal("145.00"),
            currency="USD",
        )
        db.add(price)
        db.commit()

        repo = PriceRepository(db)
        found = repo.find_by_asset_and_date(test_asset.id, target_date)
        assert found is not None
        assert found.closing_price == Decimal("145.00")

    def test_find_by_asset_and_date_returns_none_for_missing_date(self, db, test_asset):
        """Returns None if no price exists for the specified date."""
        repo = PriceRepository(db)
        missing_date = date.today() - timedelta(days=100)
        found = repo.find_by_asset_and_date(test_asset.id, missing_date)
        assert found is None

    def test_find_latest_by_assets_batch(self, db, test_asset):
        """Can find latest prices for multiple assets at once."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_today = AssetPrice(
            asset_id=test_asset.id,
            date=today,
            closing_price=Decimal("150.00"),
            currency="USD",
        )
        price_yesterday = AssetPrice(
            asset_id=test_asset.id,
            date=yesterday,
            closing_price=Decimal("148.00"),
            currency="USD",
        )
        db.add_all([price_today, price_yesterday])
        db.commit()

        repo = PriceRepository(db)
        prices = repo.find_latest_by_assets([test_asset.id])
        assert test_asset.id in prices
        assert len(prices[test_asset.id]) == 2
        # First price should be the most recent
        assert prices[test_asset.id][0].date == today
        assert prices[test_asset.id][1].date == yesterday

    def test_find_latest_by_assets_empty_list(self, db):
        """Returns empty dict for empty asset list."""
        repo = PriceRepository(db)
        prices = repo.find_latest_by_assets([])
        assert prices == {}

    def test_find_latest_by_assets_missing_asset(self, db):
        """Returns empty dict for non-existent asset ID."""
        repo = PriceRepository(db)
        prices = repo.find_latest_by_assets([99999])
        assert prices == {}

    def test_find_price_history(self, db, test_asset):
        """Can retrieve price history for date range."""
        today = date.today()
        for i in range(5):
            price = AssetPrice(
                asset_id=test_asset.id,
                date=today - timedelta(days=i),
                closing_price=Decimal("150.00") - Decimal(str(i)),
                currency="USD",
            )
            db.add(price)
        db.commit()

        repo = PriceRepository(db)
        history = repo.find_price_history(
            test_asset.id,
            start_date=today - timedelta(days=4),
            end_date=today,
        )
        assert len(history) == 5
        # Should be ordered by date ascending
        assert history[0].date == today - timedelta(days=4)
        assert history[-1].date == today

    def test_find_price_history_partial_range(self, db, test_asset):
        """Returns only prices within the specified date range."""
        today = date.today()
        # Add 10 days of prices
        for i in range(10):
            price = AssetPrice(
                asset_id=test_asset.id,
                date=today - timedelta(days=i),
                closing_price=Decimal("150.00"),
                currency="USD",
            )
            db.add(price)
        db.commit()

        repo = PriceRepository(db)
        # Request only 3 days
        history = repo.find_price_history(
            test_asset.id,
            start_date=today - timedelta(days=2),
            end_date=today,
        )
        assert len(history) == 3

    def test_find_price_history_empty(self, db, test_asset):
        """Returns empty list when no prices in range."""
        repo = PriceRepository(db)
        history = repo.find_price_history(
            test_asset.id,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today(),
        )
        assert len(history) == 0

    def test_find_previous_close(self, db, test_asset):
        """Can find the most recent price before a given date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        price_yesterday = AssetPrice(
            asset_id=test_asset.id,
            date=yesterday,
            closing_price=Decimal("149.00"),
            currency="USD",
        )
        price_day_before = AssetPrice(
            asset_id=test_asset.id,
            date=day_before,
            closing_price=Decimal("148.00"),
            currency="USD",
        )
        db.add_all([price_yesterday, price_day_before])
        db.commit()

        repo = PriceRepository(db)
        previous = repo.find_previous_close(test_asset.id, today)
        assert previous is not None
        assert previous.date == yesterday
        assert previous.closing_price == Decimal("149.00")

    def test_find_previous_close_returns_none_if_no_prior_prices(self, db, test_asset):
        """Returns None if no prices exist before the given date."""
        repo = PriceRepository(db)
        previous = repo.find_previous_close(test_asset.id, date.today())
        assert previous is None
