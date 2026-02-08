"""Currency exchange rate service."""

import logging
from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for managing currency exchange rates.

    Instance-based: accepts a db session in __init__ so callers don't
    pass it to every method.  ``fetch_exchange_rate`` remains a
    @staticmethod because it is pure I/O with no database access.
    """

    SUPPORTED_CURRENCIES = ["USD", "ILS", "CAD", "EUR", "GBP"]

    def __init__(self, db: Session) -> None:
        self._db = db

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
        rate = (
            self._db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date == target_date,
            )
            .first()
        )

        if rate:
            return rate.rate

        # Not cached, fetch from Yahoo Finance
        fetched_rate = CurrencyService.fetch_exchange_rate(from_currency, to_currency)

        if fetched_rate:
            rate = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=fetched_rate,
                date=target_date,
            )
            self._db.add(rate)
            try:
                self._db.commit()
            except Exception as e:
                logger.error(f"Error saving exchange rate: {str(e)}")
                self._db.rollback()

            return fetched_rate

        return None

    @staticmethod
    def fetch_exchange_rate(from_currency: str, to_currency: str) -> Decimal | None:
        """Fetch current exchange rate from Yahoo Finance.

        Pure I/O -- no database access, so this stays as a @staticmethod.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Exchange rate as Decimal, or None if fetch fails
        """
        try:
            symbol = f"{from_currency}{to_currency}=X"

            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")

            if data.empty:
                logger.warning(f"No data for forex pair {symbol}")
                return None

            rate = data["Close"].iloc[-1]
            return Decimal(str(round(rate, 6)))

        except Exception as e:
            logger.error(f"Error fetching exchange rate {from_currency}/{to_currency}: {str(e)}")
            return None

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

                existing = (
                    self._db.query(ExchangeRate)
                    .filter(
                        ExchangeRate.from_currency == from_curr,
                        ExchangeRate.to_currency == to_curr,
                        ExchangeRate.date == target_date,
                    )
                    .first()
                )

                if existing:
                    logger.debug(f"Rate {from_curr}/{to_curr} already exists for {target_date}")
                    stats["updated"] += 1
                    continue

                rate = CurrencyService.fetch_exchange_rate(from_curr, to_curr)

                if rate:
                    exchange_rate = ExchangeRate(
                        from_currency=from_curr, to_currency=to_curr, rate=rate, date=target_date
                    )
                    self._db.add(exchange_rate)
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

        existing_dates = set(
            row[0]
            for row in self._db.query(ExchangeRate.date)
            .filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date >= start_date,
                ExchangeRate.date <= end_date,
            )
            .all()
        )

        symbol = f"{from_currency}{to_currency}=X"
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
            )
        except Exception as e:
            logger.error(f"Failed to fetch exchange rate history for {symbol}: {e}")
            return 0

        if history.empty:
            logger.warning(f"No exchange rate data for {symbol}")
            return 0

        count = 0
        for idx, row in history.iterrows():
            rate_date = idx.date()

            if rate_date in existing_dates:
                continue

            close_rate = row.get("Close")
            if close_rate is None or close_rate <= 0:
                continue

            rate_record = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                date=rate_date,
                rate=Decimal(str(close_rate)),
            )
            self._db.add(rate_record)
            count += 1

        if count > 0:
            self._db.commit()
            logger.info(f"Inserted {count} historical rates for {symbol}")

        return count
