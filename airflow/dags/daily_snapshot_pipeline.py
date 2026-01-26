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
    GET_ACTIVE_ACCOUNTS,
    GET_ACTIVE_HOLDINGS_ASSETS,
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
            # Get all assets that have holdings
            assets = session.execute(text(GET_ACTIVE_HOLDINGS_ASSETS)).fetchall()

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

    @task(task_id="create_snapshots")
    def create_snapshots(
        exchange_rate_stats: dict[str, int | list[str]],
        asset_price_stats: dict[str, int | list[str] | str],
    ) -> dict[str, int | str | float]:
        """Create portfolio snapshots for yesterday (running at midnight UTC)."""
        logger.info(f"Exchange rates updated: {exchange_rate_stats['updated']}")
        logger.info(f"Asset prices updated: {asset_price_stats['updated']}")

        import requests

        session = SessionLocal()

        try:
            # Get all active accounts
            accounts = session.execute(text(GET_ACTIVE_ACCOUNTS)).fetchall()

            # Running at midnight UTC, snapshot is for yesterday
            snapshot_date = date.today() - timedelta(days=1)

            stats = {
                "date": str(snapshot_date),
                "total_accounts": len(accounts),
                "created": 0,
                "skipped": 0,
                "failed": 0,
                "total_value_usd": 0.0,
            }

            # Call the snapshot creation API once for all accounts
            try:
                logger.info("Creating snapshots for all accounts")

                response = requests.post(
                    f"{BACKEND_URL}/api/snapshots/create",
                    params={
                        "snapshot_date": str(snapshot_date),
                        "entity_id": None,  # Will snapshot all accounts
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    result = response.json()

                    for account_id, account_name in accounts:
                        account_stats = next(
                            (
                                acc
                                for acc in result.get("accounts", [])
                                if acc["account_id"] == account_id
                            ),
                            None,
                        )

                        if account_stats:
                            stats["created"] += 1
                            stats["total_value_usd"] += account_stats["value_usd"]
                            logger.info(
                                f"Created snapshot for {account_name}: ${account_stats['value_usd']:.2f} USD"
                            )
                        else:
                            stats["skipped"] += 1
                            logger.info(f"Skipped {account_name}: Already exists or no holdings")
                else:
                    stats["failed"] = len(accounts)
                    logger.error(f"API error: {response.status_code} - {response.text}")

            except Exception as e:
                stats["failed"] = len(accounts)
                logger.error(f"Error creating snapshots: {str(e)}")

            logger.info(
                f"Snapshot creation complete: {stats['created']} created, "
                f"{stats['skipped']} skipped, {stats['failed']} failed"
            )
            logger.info(f"Total portfolio value: ${stats['total_value_usd']:,.2f} USD")

            return stats

        except Exception as e:
            logger.error(f"Snapshot creation failed: {str(e)}")
            raise
        finally:
            session.close()

    # Define task dependencies
    exchange_rate_stats = fetch_exchange_rates()
    asset_price_stats = fetch_asset_prices()
    snapshot_stats = create_snapshots(exchange_rate_stats, asset_price_stats)

    # Both rates and prices must complete before snapshots
    [exchange_rate_stats, asset_price_stats] >> snapshot_stats


# Instantiate the DAG
dag_instance = daily_snapshot_pipeline()
