"""Currency exchange rate service."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.market_data.yfinance_client import YFinanceClient
from app.services.repositories.exchange_rate_repository import ExchangeRateRepository

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for managing currency exchange rates.

    Instance-based: accepts a db session in __init__ so callers don't
    pass it to every method.  ``fetch_exchange_rate`` remains a
    @staticmethod because it is pure I/O with no database access.
    """

    SUPPORTED_CURRENCIES = ["USD", "ILS", "CAD", "EUR", "GBP"]

    def __init__(self, db: Session, yf_client: YFinanceClient | None = None) -> None:
        self._db = db
        self._rate_repo = ExchangeRateRepository(db)
        self._yf_client = yf_client or YFinanceClient()

    def get_exchange_rate(
        self, from_currency: str, to_currency: str, target_date: date | None = None
    ) -> Decimal | None:
        """Get exchange rate for a specific date.

        Args:
            from_currency: Source currency code (e.g., "CAD")
            to_currency: Target currency code (e.g., "USD")
            target_date: Date for the exchange rate (default: today)

        Returns:
            Exchange rate as Decimal, or None if not found
        """
        if not target_date:
            target_date = date.today()

        if from_currency == to_currency:
            return Decimal("1.0")

        # Try to find cached rate
        rate = self._rate_repo.find_by_pair_and_date(from_currency, to_currency, target_date)

        if rate:
            return rate.rate

        # Not cached, fetch from Yahoo Finance
        fetched_rate = self.fetch_exchange_rate(from_currency, to_currency)

        if fetched_rate:
            self._rate_repo.create(from_currency, to_currency, fetched_rate, target_date)
            try:
                self._db.commit()
            except Exception as e:
                logger.error(f"Error saving exchange rate: {str(e)}")
                self._db.rollback()

            return fetched_rate

        return None

    def fetch_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal | None:
        """Fetch current exchange rate from Yahoo Finance via YFinanceClient.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Exchange rate as Decimal, or None if fetch fails
        """
        return self._yf_client.get_forex_rate(from_currency, to_currency)

    def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        target_date: date | None = None,
    ) -> Decimal | None:
        """Convert an amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            target_date: Date for exchange rate (default: today)

        Returns:
            Converted amount, or None if conversion fails
        """
        if from_currency == to_currency:
            return amount

        rate = self.get_exchange_rate(from_currency, to_currency, target_date)

        if rate:
            return amount * rate

        return None

    def update_all_rates(self) -> dict[str, int | list[str]]:
        """Update exchange rates for all supported currency pairs.

        Returns:
            Statistics dict with success/failure counts
        """
        stats = {"total": 0, "updated": 0, "failed": 0, "pairs": []}

        target_date = date.today()

        for from_curr in self.SUPPORTED_CURRENCIES:
            for to_curr in self.SUPPORTED_CURRENCIES:
                if from_curr == to_curr:
                    continue

                stats["total"] += 1

                existing = self._rate_repo.find_by_pair_and_date(from_curr, to_curr, target_date)

                if existing:
                    logger.debug(f"Rate {from_curr}/{to_curr} already exists for {target_date}")
                    stats["updated"] += 1
                    continue

                rate = self.fetch_exchange_rate(from_curr, to_curr)

                if rate:
                    self._rate_repo.create(from_curr, to_curr, rate, target_date)
                    stats["updated"] += 1
                    stats["pairs"].append(f"{from_curr}/{to_curr}")
                    logger.info(f"Updated rate {from_curr}/{to_curr} = {rate}")
                else:
                    stats["failed"] += 1
                    logger.warning(f"Failed to fetch rate {from_curr}/{to_curr}")

        try:
            self._db.commit()
        except Exception as e:
            logger.error(f"Error committing exchange rates: {str(e)}")
            self._db.rollback()
            stats["failed"] = stats["total"]
            stats["updated"] = 0

        return stats

    def fetch_and_store_historical_rates(
        self,
        from_currency: str,
        to_currency: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """Fetch historical exchange rates and store in exchange_rates table.

        Uses yfinance for the full date range in one API call.
        Skips dates that already have rates in the database.

        Args:
            from_currency: Source currency (e.g., "USD")
            to_currency: Target currency (e.g., "ILS")
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Number of new rates inserted
        """
        if from_currency == to_currency:
            return 0

        existing_dates = self._rate_repo.find_dates_in_range(
            from_currency, to_currency, start_date, end_date
        )

        rows = self._yf_client.get_forex_history(
            from_currency, to_currency, start=start_date, end=end_date
        )

        if not rows:
            logger.warning(f"No exchange rate data for {from_currency}/{to_currency}")
            return 0

        count = 0
        for row in rows:
            if row.date in existing_dates:
                continue
            if row.close is None or row.close <= 0:
                continue
            self._rate_repo.create(from_currency, to_currency, row.close, row.date)
            count += 1

        if count > 0:
            self._db.commit()
            logger.info(f"Inserted {count} historical rates for {from_currency}/{to_currency}")

        return count
