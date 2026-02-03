"""
Daily Snapshot Pipeline DAG

Creates end-of-day portfolio snapshots at midnight UTC:
1. Fetch exchange rates for all currency pairs
2. Fetch yesterday's closing prices for stocks (via Yahoo Finance)
3. Fetch crypto closing prices at midnight UTC (via CoinGecko)
4. Create portfolio snapshots with accurate valuations

Schedule: Daily at midnight UTC (00:00)
"""

import logging
import os
from datetime import date, datetime, timedelta

import yfinance as yf
from airflow.sdk import dag, task
from dotenv import load_dotenv

# Import SQL queries and shared database
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

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from backend .env
load_dotenv("/opt/airflow/backend/.env")

# Backend API URL (through host.docker.internal)
BACKEND_URL = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")

# Supported currency pairs
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
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


@dag(
    dag_id="daily_snapshot_pipeline",
    default_args=default_args,
    description="Daily end-of-day snapshots with exchange rates and asset prices",
    schedule="0 0 * * *",  # Midnight UTC daily
    start_date=datetime(2026, 1, 1),
    catchup=False,  # Don't run historical DAGs
    tags=["portfolio", "daily", "snapshots"],
)
def daily_snapshot_pipeline():
    """Define the daily data pipeline DAG."""

    @task(task_id="fetch_exchange_rates")
    def fetch_exchange_rates() -> dict[str, int | list[str]]:
        """Fetch and store exchange rates for all supported currency pairs."""
        session = SessionLocal()

        try:
            # Running at midnight UTC, capture yesterday's rates
            snapshot_date = date.today() - timedelta(days=1)
            stats = {"total": len(CURRENCY_PAIRS), "updated": 0, "failed": 0, "pairs": []}

            for from_curr, to_curr in CURRENCY_PAIRS:
                try:
                    # Check if rate already exists for snapshot_date
                    existing = session.execute(
                        text(CHECK_EXCHANGE_RATE_EXISTS),
                        {"from_curr": from_curr, "to_curr": to_curr, "date": snapshot_date},
                    ).first()

                    if existing:
                        logger.info(
                            f"Rate {from_curr}/{to_curr} already exists for {snapshot_date}"
                        )
                        stats["updated"] += 1
                        continue

                    # Fetch rate using yfinance
                    ticker_symbol = f"{from_curr}{to_curr}=X"
                    ticker = yf.Ticker(ticker_symbol)
                    hist = ticker.history(period="1d")

                    if not hist.empty and "Close" in hist.columns:
                        rate = float(hist["Close"].iloc[-1])

                        # Insert new rate
                        session.execute(
                            text(INSERT_EXCHANGE_RATE),
                            {
                                "from_curr": from_curr,
                                "to_curr": to_curr,
                                "rate": rate,
                                "date": snapshot_date,
                            },
                        )
                        session.commit()

                        logger.info(f"Updated {from_curr}/{to_curr} = {rate}")
                        stats["updated"] += 1
                        stats["pairs"].append(f"{from_curr}/{to_curr}")
                    else:
                        logger.warning(f"No data for {from_curr}/{to_curr}")
                        stats["failed"] += 1

                except Exception as e:
                    logger.error(f"Failed to fetch {from_curr}/{to_curr}: {str(e)}")
                    stats["failed"] += 1
                    session.rollback()
                    continue

            if stats["failed"] > 0:
                logger.warning(f"Failed to update {stats['failed']} currency pairs")

            return stats

        except Exception as e:
            logger.error(f"Exchange rate update failed: {str(e)}")
            raise
        finally:
            session.close()

    @task(task_id="fetch_asset_prices", pool="db_write_pool")
    def fetch_asset_prices() -> dict[str, int | list[str] | str]:
        """
        Fetch and store YESTERDAY'S closing prices for non-crypto assets.

        NOTE: This DAG runs at midnight UTC, so we fetch yesterday's
        closing prices for accurate end-of-day snapshots.
        """
        session = SessionLocal()

        try:
            # Only fetch non-crypto assets (crypto handled by fetch_crypto_prices)
            assets = session.execute(text(GET_NON_CRYPTO_ASSETS)).fetchall()

            # Running at midnight UTC, capture yesterday's close
            snapshot_date = date.today() - timedelta(days=1)

            stats: dict[str, int | list[str] | str] = {
                "total": len(assets),
                "updated": 0,
                "failed": 0,
                "errors": [],
                "target_date": str(snapshot_date),
            }

            for asset_id, symbol, currency in assets:
                try:
                    # Check if we already have a closing price for snapshot_date
                    existing = session.execute(
                        text(CHECK_ASSET_PRICE_EXISTS),
                        {"asset_id": asset_id, "date": snapshot_date},
                    ).first()

                    if existing:
                        logger.info(f"Already have closing price for {symbol} on {snapshot_date}")
                        stats["updated"] += 1
                        continue

                    # Fetch yesterday's closing price (running at midnight UTC)
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(
                        start=snapshot_date, end=snapshot_date + timedelta(days=1)
                    )

                    if not hist.empty and "Close" in hist.columns:
                        closing_price = float(hist["Close"].iloc[0])

                        # Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
                        # Convert to ILS for consistency
                        if symbol.endswith(".TA"):
                            closing_price = closing_price / 100

                        # Store yesterday's closing price
                        session.execute(
                            text(INSERT_ASSET_PRICE),
                            {
                                "asset_id": asset_id,
                                "date": snapshot_date,
                                "closing_price": closing_price,
                                "currency": currency,
                                "source": "Yahoo Finance",
                            },
                        )
                        session.commit()

                        logger.info(
                            f"Stored closing price for {symbol}: {closing_price} {currency}"
                        )
                        stats["updated"] += 1
                    else:
                        error_msg = f"{symbol}: No closing price data for {snapshot_date}"
                        stats["errors"].append(error_msg)
                        stats["failed"] += 1
                        logger.warning(error_msg)

                except Exception as e:
                    error_msg = f"{symbol}: {str(e)}"
                    stats["errors"].append(error_msg)
                    stats["failed"] += 1
                    logger.error(f"Failed to fetch closing price for {symbol}: {str(e)}")
                    session.rollback()
                    continue

            logger.info(
                f"Asset price update complete: {stats['updated']} updated, {stats['failed']} failed"
            )
            return stats

        except Exception as e:
            logger.error(f"Asset price update failed: {str(e)}")
            raise
        finally:
            session.close()

    @task(task_id="fetch_crypto_prices", pool="db_write_pool")
    def fetch_crypto_prices() -> dict[str, int | list[str] | str]:
        """
        Fetch and store crypto prices using CoinGecko.

        Crypto markets are 24/7, so there's no true "closing price". We fetch the
        current spot price at midnight UTC and use it as the day's reference price.
        This is acceptable for day-change calculations since DAG runs immediately
        at midnight with minimal scheduler delay.

        Note: If the DAG retries significantly later (e.g., 00:15+), prices may
        differ slightly from midnight. The idempotency check prevents overwrites.
        """
        import sys

        # Add backend to path for CoinGecko client import
        # (backend package not on Airflow worker's PYTHONPATH)
        if "/opt/airflow/backend" not in sys.path:
            sys.path.insert(0, "/opt/airflow/backend")
        from app.services.market_data.coingecko_client import CoinGeckoClient

        session = SessionLocal()

        try:
            assets = session.execute(text(GET_CRYPTO_ASSETS)).fetchall()

            # Running at midnight UTC, store as yesterday's price
            snapshot_date = date.today() - timedelta(days=1)

            stats: dict[str, int | list[str] | str] = {
                "total": len(assets),
                "inserted": 0,
                "skipped": 0,
                "failed": 0,
                "errors": [],
                "target_date": str(snapshot_date),
            }

            if not assets:
                logger.info("No crypto assets found")
                return stats

            # Filter out assets that already have prices for this date
            assets_needing_prices = []
            for asset_id, symbol, _currency in assets:
                existing = session.execute(
                    text(CHECK_ASSET_PRICE_EXISTS),
                    {"asset_id": asset_id, "date": snapshot_date},
                ).first()

                if existing:
                    logger.info(f"Already have closing price for {symbol} on {snapshot_date}")
                    stats["skipped"] += 1
                else:
                    assets_needing_prices.append((asset_id, symbol))

            if not assets_needing_prices:
                logger.info("All crypto prices already up to date")
                return stats

            # Batch fetch only the prices we need in one API call
            symbols = [symbol for _, symbol in assets_needing_prices]
            client = CoinGeckoClient()
            prices = client.get_current_prices(symbols, "usd")

            # Check for total API failure (empty response when we expected prices)
            if not prices and assets_needing_prices:
                error_msg = "CoinGecko API returned no prices - possible API outage"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            for asset_id, symbol in assets_needing_prices:
                try:
                    price = prices.get(symbol)
                    if price is not None:
                        session.execute(
                            text(INSERT_ASSET_PRICE),
                            {
                                "asset_id": asset_id,
                                "date": snapshot_date,
                                "closing_price": float(price),
                                "currency": "USD",
                                "source": "CoinGecko",
                            },
                        )
                        session.commit()

                        logger.info(f"Stored closing price for {symbol}: {price} USD")
                        stats["inserted"] += 1
                    else:
                        error_msg = f"{symbol}: No price from CoinGecko"
                        stats["errors"].append(error_msg)
                        stats["failed"] += 1
                        logger.warning(error_msg)

                except Exception as e:
                    error_msg = f"{symbol}: {str(e)}"
                    stats["errors"].append(error_msg)
                    stats["failed"] += 1
                    logger.error(f"Failed to store closing price for {symbol}: {str(e)}")
                    session.rollback()
                    continue

            logger.info(
                f"Crypto price update complete: {stats['inserted']} inserted, "
                f"{stats['skipped']} skipped, {stats['failed']} failed"
            )
            return stats

        except Exception as e:
            logger.error(f"Crypto price update failed: {str(e)}")
            raise
        finally:
            session.close()

    @task(task_id="create_snapshots")
    def create_snapshots(
        exchange_rate_stats: dict[str, int | list[str]],
        asset_price_stats: dict[str, int | list[str] | str],
        crypto_price_stats: dict[str, int | list[str] | str],
    ) -> dict[str, int | str | float]:
        """Create portfolio snapshots for yesterday (running at midnight UTC)."""
        import sys

        # Add backend to path for SnapshotService import
        if "/opt/airflow/backend" not in sys.path:
            sys.path.insert(0, "/opt/airflow/backend")
        from app.services.portfolio.snapshot_service import SnapshotService

        logger.info(f"Exchange rates updated: {exchange_rate_stats['updated']}")
        logger.info(f"Asset prices updated: {asset_price_stats['updated']}")
        logger.info(
            f"Crypto prices: {crypto_price_stats.get('inserted', 0)} inserted, "
            f"{crypto_price_stats.get('skipped', 0)} skipped"
        )

        # Running at midnight UTC, snapshot is for yesterday
        snapshot_date = date.today() - timedelta(days=1)

        session = SessionLocal()
        try:
            result = SnapshotService.create_portfolio_snapshot(
                db=session,
                snapshot_date=snapshot_date,
                allowed_account_ids=None,  # None = all accounts in system
            )
        finally:
            session.close()

        # Log per-account details
        for account_info in result.get("accounts", []):
            logger.info(
                f"Created snapshot for {account_info['account_name']}: "
                f"${account_info['value_usd']:.2f} USD"
            )

        snapshots_created = result.get("snapshots_created", 0)
        total_value_usd = float(result.get("total_value_usd", 0))

        logger.info(f"Snapshot creation complete: {snapshots_created} snapshots created")
        logger.info(f"Total portfolio value: ${total_value_usd:,.2f} USD")

        return {
            "date": str(snapshot_date),
            "created": snapshots_created,
            "total_value_usd": total_value_usd,
        }

    # Define task dependencies (TaskFlow API creates implicit deps via argument passing)
    exchange_rate_stats = fetch_exchange_rates()
    asset_price_stats = fetch_asset_prices()
    crypto_price_stats = fetch_crypto_prices()
    create_snapshots(exchange_rate_stats, asset_price_stats, crypto_price_stats)


# Instantiate the DAG
dag_instance = daily_snapshot_pipeline()
