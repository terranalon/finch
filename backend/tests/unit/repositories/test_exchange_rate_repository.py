"""Tests for ExchangeRateRepository."""

from datetime import date, timedelta
from decimal import Decimal

from app.models.exchange_rate import ExchangeRate
from app.services.repositories.exchange_rate_repository import ExchangeRateRepository


class TestExchangeRateRepository:
    """Test cases for ExchangeRateRepository."""

    def test_find_by_pair_and_date_returns_rate(self, db):
        """Returns matching exchange rate."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="ILS",
            rate=Decimal("3.700000"),
            date=date(2024, 6, 15),
        )
        db.add(rate)
        db.commit()

        repo = ExchangeRateRepository(db)
        found = repo.find_by_pair_and_date("USD", "ILS", date(2024, 6, 15))
        assert found is not None
        assert found.rate == Decimal("3.700000")

    def test_find_by_pair_and_date_returns_none_for_missing(self, db):
        """Returns None when no rate exists."""
        repo = ExchangeRateRepository(db)
        found = repo.find_by_pair_and_date("CHF", "SEK", date(1999, 1, 1))
        assert found is None

    def test_find_by_pair_and_date_wrong_pair_returns_none(self, db):
        """Returns None when pair doesn't match."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="ILS",
            rate=Decimal("3.700000"),
            date=date(2024, 6, 15),
        )
        db.add(rate)
        db.commit()

        repo = ExchangeRateRepository(db)
        found = repo.find_by_pair_and_date("EUR", "ILS", date(2024, 6, 15))
        assert found is None

    def test_find_dates_in_range(self, db):
        """Returns set of dates that have rates."""
        for i in range(5):
            db.add(
                ExchangeRate(
                    from_currency="USD",
                    to_currency="ILS",
                    rate=Decimal("3.700000"),
                    date=date(2024, 6, 10) + timedelta(days=i),
                )
            )
        db.commit()

        repo = ExchangeRateRepository(db)
        dates = repo.find_dates_in_range(
            "USD", "ILS", date(2024, 6, 11), date(2024, 6, 13)
        )
        assert dates == {date(2024, 6, 11), date(2024, 6, 12), date(2024, 6, 13)}

    def test_find_dates_in_range_empty(self, db):
        """Returns empty set when no rates in range."""
        repo = ExchangeRateRepository(db)
        dates = repo.find_dates_in_range("CHF", "SEK", date(1999, 1, 1), date(1999, 1, 5))
        assert dates == set()

    def test_create_persists_rate(self, db):
        """Creates and flushes a new rate."""
        repo = ExchangeRateRepository(db)
        created = repo.create("USD", "ILS", Decimal("3.710000"), date(2024, 7, 1))
        assert created.id is not None
        assert created.from_currency == "USD"
        assert created.rate == Decimal("3.710000")
