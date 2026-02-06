"""Service for fetching and storing exchange rates."""

import logging
from datetime import date, timedelta

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Currency pairs to fetch (matches current DAG)
CURRENCY_PAIRS = [
    ("USD", "ILS"),
    ("USD", "CAD"),
    ("USD", "EUR"),
    ("USD", "GBP"),
    ("CAD", "USD"),
    ("EUR", "USD"),
    ("GBP", "USD"),
    ("ILS", "USD"),
]

CHECK_EXCHANGE_RATE_EXISTS = """
SELECT 1 FROM exchange_rates
WHERE from_currency = :from_curr
AND to_currency = :to_curr
AND date = :date
"""

INSERT_EXCHANGE_RATE = """
INSERT INTO exchange_rates (from_currency, to_currency, rate, date)
VALUES (:from_curr, :to_curr, :rate, :date)
"""


class ExchangeRateService:
    """Service for refreshing exchange rates from yfinance."""

    @staticmethod
    def refresh(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store exchange rates for the given date.

        Args:
            db: Database session
            target_date: Date to fetch rates for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        stats: dict = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "pairs": [],
        }

        for from_curr, to_curr in CURRENCY_PAIRS:
            try:
                existing = db.execute(
                    text(CHECK_EXCHANGE_RATE_EXISTS),
                    {"from_curr": from_curr, "to_curr": to_curr, "date": target_date},
                ).first()

                if existing:
                    logger.info("Rate %s/%s already exists for %s", from_curr, to_curr, target_date)
                    stats["skipped"] += 1
                    continue

                ticker_symbol = f"{from_curr}{to_curr}=X"
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="5d")

                if not hist.empty and "Close" in hist.columns:
                    rate = float(hist["Close"].iloc[-1])

                    db.execute(
                        text(INSERT_EXCHANGE_RATE),
                        {
                            "from_curr": from_curr,
                            "to_curr": to_curr,
                            "rate": rate,
                            "date": target_date,
                        },
                    )
                    db.commit()

                    logger.info("Updated %s/%s = %s", from_curr, to_curr, rate)
                    stats["updated"] += 1
                    stats["pairs"].append(f"{from_curr}/{to_curr}")
                else:
                    logger.warning("No data for %s/%s", from_curr, to_curr)
                    stats["failed"] += 1

            except Exception:
                logger.exception("Failed to fetch %s/%s", from_curr, to_curr)
                stats["failed"] += 1
                db.rollback()

        return stats
