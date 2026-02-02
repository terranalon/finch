"""
Historical Data Backfill DAG

One-time DAG for backfilling historical asset prices and exchange rates.
This is needed to generate accurate historical portfolio snapshots.

Schedule: Manual trigger only (no automatic schedule)
"""

import logging
import os
import sys
from datetime import date, datetime, timedelta

# Add dags folder to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
from airflow.sdk import dag, task
from dotenv import load_dotenv
from queries import (
    CHECK_ASSET_PRICE_EXISTS,
    CHECK_EXCHANGE_RATE_EXISTS,
    GET_CRYPTO_ASSETS,
    GET_NON_CRYPTO_ASSETS,
    INSERT_ASSET_PRICE,
    INSERT_EXCHANGE_RATE,
)
from shared_db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("/opt/airflow/backend/.env")

# Currency pairs to backfill
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

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="backfill_historical_data",
    default_args=default_args,
    description="One-time backfill of historical asset prices, crypto prices, and exchange rates",
    schedule=None,  # Manual trigger only
    start_date=datetime(2024, 5, 1),
    catchup=False,
    tags=["portfolio", "backfill", "historical", "one-time", "crypto"],
    params={
        "start_date": "2017-01-01",  # Far enough back for crypto history
        "end_date": None,  # Defaults to yesterday
    },
)
def backfill_historical_data():
    """One-time DAG to backfill historical prices for snapshot generation.

    - Stocks/ETFs: Uses Yahoo Finance
    - Crypto: Uses CryptoCompare (supports full history back to coin inception)
    - Exchange rates: Uses Yahoo Finance currency pairs
    """

    @task(task_id="backfill_exchange_rates", pool="db_write_pool")
    def backfill_exchange_rates(**context) -> dict:
        """Backfill historical exchange rates."""
        params = context["params"]
        start_str = params.get("start_date", "2024-05-01")
        end_str = params.get("end_date")

        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = (
            datetime.strptime(end_str, "%Y-%m-%d").date()
            if end_str
            else date.today() - timedelta(days=1)
        )

        session = SessionLocal()

        try:
            stats = {
                "start_date": str(start),
                "end_date": str(end),
                "total_pairs": len(CURRENCY_PAIRS),
                "rates_inserted": 0,
                "rates_skipped": 0,
                "errors": [],
            }

            for from_curr, to_curr in CURRENCY_PAIRS:
                try:
                    ticker_symbol = f"{from_curr}{to_curr}=X"
                    ticker = yf.Ticker(ticker_symbol)
                    hist = ticker.history(start=start, end=end + timedelta(days=1))

                    if hist.empty:
                        stats["errors"].append(f"No data for {from_curr}/{to_curr}")
                        continue

                    inserted = 0
                    skipped = 0

                    for idx, row in hist.iterrows():
                        rate_date = idx.date()
                        rate = float(row["Close"])

                        existing = session.execute(
                            text(CHECK_EXCHANGE_RATE_EXISTS),
                            {"from_curr": from_curr, "to_curr": to_curr, "date": rate_date},
                        ).first()

                        if existing:
                            skipped += 1
                            continue

                        session.execute(
                            text(INSERT_EXCHANGE_RATE),
                            {
                                "from_curr": from_curr,
                                "to_curr": to_curr,
                                "rate": rate,
                                "date": rate_date,
                            },
                        )
                        inserted += 1

                    session.commit()
                    stats["rates_inserted"] += inserted
                    stats["rates_skipped"] += skipped
                    logger.info(
                        f"Backfilled {from_curr}/{to_curr}: {inserted} inserted, {skipped} skipped"
                    )

                except Exception as e:
                    stats["errors"].append(f"{from_curr}/{to_curr}: {str(e)}")
                    session.rollback()
                    logger.error(f"Failed {from_curr}/{to_curr}: {e}")

            logger.info(f"Exchange rate backfill complete: {stats['rates_inserted']} inserted")
            return stats

        finally:
            session.close()

    @task(task_id="backfill_asset_prices", pool="db_write_pool")
    def backfill_asset_prices(**context) -> dict:
        """Backfill historical asset prices (non-crypto only, uses Yahoo Finance)."""
        params = context["params"]
        start_str = params.get("start_date", "2024-05-01")
        end_str = params.get("end_date")

        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = (
            datetime.strptime(end_str, "%Y-%m-%d").date()
            if end_str
            else date.today() - timedelta(days=1)
        )

        session = SessionLocal()

        try:
            # Get non-crypto assets only (stocks, ETFs, etc.)
            assets = session.execute(text(GET_NON_CRYPTO_ASSETS)).fetchall()

            stats = {
                "start_date": str(start),
                "end_date": str(end),
                "total_assets": len(assets),
                "assets_processed": 0,
                "prices_inserted": 0,
                "prices_skipped": 0,
                "errors": [],
            }

            for asset_id, symbol, currency in assets:
                # Skip cash assets
                if symbol in ("USD", "CAD", "EUR", "GBP", "ILS"):
                    logger.info(f"Skipping cash asset: {symbol}")
                    continue

                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start, end=end + timedelta(days=1))

                    if hist.empty:
                        stats["errors"].append(f"{symbol}: No historical data")
                        logger.warning(f"No data for {symbol}")
                        continue

                    inserted = 0
                    skipped = 0

                    for idx, row in hist.iterrows():
                        price_date = idx.date()
                        closing_price = float(row["Close"])

                        # Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
                        # Convert to ILS for consistency
                        if symbol.endswith(".TA"):
                            closing_price = closing_price / 100

                        existing = session.execute(
                            text(CHECK_ASSET_PRICE_EXISTS),
                            {"asset_id": asset_id, "date": price_date},
                        ).first()

                        if existing:
                            skipped += 1
                            continue

                        session.execute(
                            text(INSERT_ASSET_PRICE),
                            {
                                "asset_id": asset_id,
                                "date": price_date,
                                "closing_price": closing_price,
                                "currency": currency,
                                "source": "Yahoo Finance (backfill)",
                            },
                        )
                        inserted += 1

                    session.commit()
                    stats["prices_inserted"] += inserted
                    stats["prices_skipped"] += skipped
                    stats["assets_processed"] += 1
                    logger.info(f"Backfilled {symbol}: {inserted} inserted, {skipped} skipped")

                except Exception as e:
                    stats["errors"].append(f"{symbol}: {str(e)}")
                    session.rollback()
                    logger.error(f"Failed {symbol}: {e}")

            logger.info(
                f"Asset price backfill complete: {stats['prices_inserted']} prices "
                f"for {stats['assets_processed']} assets"
            )
            return stats

        finally:
            session.close()

    @task(task_id="backfill_crypto_prices", pool="db_write_pool")
    def backfill_crypto_prices(**context) -> dict:
        """Backfill historical crypto prices using CryptoCompare API.

        CryptoCompare provides full historical data (back to coin inception),
        unlike CoinGecko's free tier which is limited to 365 days.
        """
        # Import here to avoid loading at DAG parse time
        sys.path.insert(0, "/opt/airflow/backend")
        from app.services.market_data.cryptocompare_client import CryptoCompareClient

        params = context["params"]
        start_str = params.get("start_date", "2017-01-01")  # Default to 2017 for crypto
        end_str = params.get("end_date")

        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = (
            datetime.strptime(end_str, "%Y-%m-%d").date()
            if end_str
            else date.today() - timedelta(days=1)
        )

        session = SessionLocal()
        client = CryptoCompareClient()

        try:
            # Get crypto assets only
            assets = session.execute(text(GET_CRYPTO_ASSETS)).fetchall()

            stats = {
                "start_date": str(start),
                "end_date": str(end),
                "total_assets": len(assets),
                "assets_processed": 0,
                "prices_inserted": 0,
                "prices_skipped": 0,
                "errors": [],
            }

            for asset_id, symbol, currency in assets:
                try:
                    # Fetch price history from CryptoCompare
                    history = client.get_price_history(symbol, start, end, vs_currency="USD")

                    if not history:
                        stats["errors"].append(f"{symbol}: No historical data from CryptoCompare")
                        logger.warning(f"No CryptoCompare data for {symbol}")
                        continue

                    inserted = 0
                    skipped = 0

                    for price_date, closing_price in history:
                        existing = session.execute(
                            text(CHECK_ASSET_PRICE_EXISTS),
                            {"asset_id": asset_id, "date": price_date},
                        ).first()

                        if existing:
                            skipped += 1
                            continue

                        session.execute(
                            text(INSERT_ASSET_PRICE),
                            {
                                "asset_id": asset_id,
                                "date": price_date,
                                "closing_price": float(closing_price),
                                "currency": "USD",
                                "source": "CryptoCompare (backfill)",
                            },
                        )
                        inserted += 1

                    session.commit()
                    stats["prices_inserted"] += inserted
                    stats["prices_skipped"] += skipped
                    stats["assets_processed"] += 1
                    logger.info(
                        f"Backfilled crypto {symbol}: {inserted} inserted, {skipped} skipped"
                    )

                except Exception as e:
                    stats["errors"].append(f"{symbol}: {str(e)}")
                    session.rollback()
                    logger.error(f"Failed crypto {symbol}: {e}")

            logger.info(
                f"Crypto price backfill complete: {stats['prices_inserted']} prices "
                f"for {stats['assets_processed']} crypto assets"
            )
            return stats

        finally:
            session.close()

    @task(task_id="summary")
    def summary(exchange_stats: dict, price_stats: dict, crypto_stats: dict) -> dict:
        """Summarize backfill results."""
        total_prices = price_stats.get("prices_inserted", 0) + crypto_stats.get(
            "prices_inserted", 0
        )
        result = {
            "exchange_rates": exchange_stats,
            "asset_prices": price_stats,
            "crypto_prices": crypto_stats,
            "total_records_inserted": exchange_stats.get("rates_inserted", 0) + total_prices,
        }

        logger.info(f"Backfill complete: {result['total_records_inserted']} total records inserted")
        logger.info(f"  Exchange rates: {exchange_stats.get('rates_inserted', 0)}")
        logger.info(f"  Asset prices (stocks/ETFs): {price_stats.get('prices_inserted', 0)}")
        logger.info(f"  Crypto prices: {crypto_stats.get('prices_inserted', 0)}")

        all_errors = (
            exchange_stats.get("errors", [])
            + price_stats.get("errors", [])
            + crypto_stats.get("errors", [])
        )
        if all_errors:
            logger.warning("Some errors occurred during backfill:")
            for err in exchange_stats.get("errors", []):
                logger.warning(f"  Exchange: {err}")
            for err in price_stats.get("errors", []):
                logger.warning(f"  Asset: {err}")
            for err in crypto_stats.get("errors", []):
                logger.warning(f"  Crypto: {err}")

        return result

    # Run backfills in parallel, then summarize
    exchange_stats = backfill_exchange_rates()
    price_stats = backfill_asset_prices()
    crypto_stats = backfill_crypto_prices()
    summary(exchange_stats, price_stats, crypto_stats)


# Instantiate the DAG
dag_instance = backfill_historical_data()
