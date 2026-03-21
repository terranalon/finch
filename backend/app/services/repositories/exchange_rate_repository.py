"""Exchange rate data access layer."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


class ExchangeRateRepository:
    """Centralized exchange rate data access.

    Naming conventions:
    - find_* : Query that may return None or empty collection
    - create : Insert new record (uses flush, not commit)
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_pair_and_date(
        self, from_currency: str, to_currency: str, target_date: date
    ) -> ExchangeRate | None:
        """Find exchange rate for a specific currency pair and date."""
        return (
            self._db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date == target_date,
            )
            .first()
        )

    def find_most_recent_before(
        self, from_currency: str, to_currency: str, before_date: date
    ) -> ExchangeRate | None:
        """Find the most recent exchange rate before a given date (forward-fill)."""
        return (
            self._db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date < before_date,
            )
            .order_by(ExchangeRate.date.desc())
            .first()
        )

    def find_dates_in_range(
        self, from_currency: str, to_currency: str, start_date: date, end_date: date
    ) -> set[date]:
        """Find all dates that have rates for a currency pair within a range."""
        rows = (
            self._db.query(ExchangeRate.date)
            .filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date >= start_date,
                ExchangeRate.date <= end_date,
            )
            .all()
        )
        return {row[0] for row in rows}

    def create(
        self, from_currency: str, to_currency: str, rate: Decimal, target_date: date
    ) -> ExchangeRate:
        """Create a new exchange rate record. Uses flush(), not commit()."""
        exchange_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            date=target_date,
        )
        self._db.add(exchange_rate)
        self._db.flush()
        return exchange_rate
