"""Service for fetching and storing exchange rates."""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate
from app.services.market_data.yfinance_client import YFinanceClient

logger = logging.getLogger(__name__)

# Currency pairs to fetch (matches current DAG)
CURRENCY_PAIRS = (
    ("USD", "ILS"),
    ("USD", "CAD"),
    ("USD", "EUR"),
    ("USD", "GBP"),
    ("CAD", "USD"),
    ("EUR", "USD"),
    ("GBP", "USD"),
    ("ILS", "USD"),
)


class ExchangeRateService:
    """Service for refreshing exchange rates via YFinanceClient."""

    CURRENCY_PAIRS = CURRENCY_PAIRS

    def __init__(self, yf_client: YFinanceClient | None = None) -> None:
        self._yf_client = yf_client or YFinanceClient()

    def refresh(
        self, db: Session, target_date: date | None = None
    ) -> dict:
        """Fetch and store exchange rates for the given date.

        Args:
            db: Database session
            target_date: Date to fetch rates for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        updated = 0
        skipped = 0
        failed = 0
        pairs: list[str] = []

        for from_curr, to_curr in CURRENCY_PAIRS:
            try:
                existing = (
                    db.query(ExchangeRate)
                    .filter(
                        ExchangeRate.from_currency == from_curr,
                        ExchangeRate.to_currency == to_curr,
                        ExchangeRate.date == target_date,
                    )
                    .first()
                )

                if existing is not None:
                    logger.info("Rate %s/%s already exists for %s", from_curr, to_curr, target_date)
                    skipped += 1
                    continue

                rate = self._yf_client.get_forex_rate(from_curr, to_curr, target_date=target_date)

                if rate is None:
                    logger.warning("No data for %s/%s on %s", from_curr, to_curr, target_date)
                    failed += 1
                    continue

                db.add(
                    ExchangeRate(
                        from_currency=from_curr,
                        to_currency=to_curr,
                        rate=rate,
                        date=target_date,
                    )
                )
                db.commit()

                logger.info("Updated %s/%s = %s", from_curr, to_curr, rate)
                updated += 1
                pairs = [*pairs, f"{from_curr}/{to_curr}"]

            except Exception:
                logger.exception("Failed to fetch %s/%s", from_curr, to_curr)
                failed += 1
                db.rollback()

        return {
            "date": target_date,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "pairs": pairs,
        }
