"""Daily snapshot pipeline - fetches prices and creates portfolio snapshots.

This DAG runs at midnight UTC and:
1. Fetches exchange rates via backend API
2. Fetches stock prices via backend API
3. Fetches crypto prices via backend API
4. Creates portfolio snapshots via backend API

All data operations are handled by the backend - this DAG is a pure orchestrator.
"""

import logging
from datetime import date, datetime, timedelta

import requests
from airflow.sdk import dag, task
from auth_helper import get_auth_helper

logger = logging.getLogger(__name__)

# Backend API URL (Docker cross-network access)
BACKEND_URL = "http://host.docker.internal:8000"

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


def _make_api_call(endpoint: str, params: dict | None = None) -> dict:
    """Make authenticated API call to backend."""
    auth = get_auth_helper()
    url = f"{BACKEND_URL}{endpoint}"

    response = requests.post(
        url,
        params=params,
        headers=auth.get_auth_headers(),
        timeout=120,
    )

    if response.status_code == 401:
        # Token expired, force refresh and retry
        auth.force_refresh()
        response = requests.post(
            url,
            params=params,
            headers=auth.get_auth_headers(),
            timeout=120,
        )

    if response.status_code != 200:
        logger.error("API error: %s - %s", response.status_code, response.text)
        raise RuntimeError(f"API call failed: {response.text}")

    return response.json()


@dag(
    dag_id="daily_snapshot_pipeline",
    default_args=default_args,
    description="Daily end-of-day snapshots with exchange rates and asset prices",
    schedule="0 0 * * *",  # Midnight UTC daily
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["portfolio", "daily", "snapshots"],
)
def daily_snapshot_pipeline():
    """Define the daily data pipeline DAG."""

    @task(task_id="fetch_exchange_rates")
    def fetch_exchange_rates() -> dict:
        """Fetch exchange rates via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info("Fetching exchange rates for %s", snapshot_date)

        result = _make_api_call(
            "/api/market-data/exchange-rates/refresh",
            params={"target_date": str(snapshot_date)},
        )

        logger.info(
            "Exchange rates: %s updated, %s skipped, %s failed",
            result["updated"],
            result["skipped"],
            result["failed"],
        )
        return result

    @task(task_id="fetch_asset_prices", pool="db_write_pool")
    def fetch_asset_prices() -> dict:
        """Fetch stock prices via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info("Fetching stock prices for %s", snapshot_date)

        result = _make_api_call(
            "/api/market-data/stock-prices/refresh",
            params={"target_date": str(snapshot_date)},
        )

        logger.info(
            "Stock prices: %s updated, %s skipped, %s failed",
            result["updated"],
            result["skipped"],
            result["failed"],
        )
        return result

    @task(task_id="fetch_crypto_prices", pool="db_write_pool")
    def fetch_crypto_prices() -> dict:
        """Fetch crypto prices via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info("Fetching crypto prices for %s", snapshot_date)

        result = _make_api_call(
            "/api/market-data/crypto-prices/refresh",
            params={"target_date": str(snapshot_date)},
        )

        logger.info(
            "Crypto prices (%s): %s updated, %s skipped, %s failed",
            result["source"],
            result["updated"],
            result["skipped"],
            result["failed"],
        )
        return result

    @task(task_id="create_snapshots")
    def create_snapshots(
        exchange_rate_stats: dict,
        asset_price_stats: dict,
        crypto_price_stats: dict,
    ) -> dict:
        """Create portfolio snapshots via backend API."""
        snapshot_date = date.today() - timedelta(days=1)

        logger.info("Exchange rates: %s updated", exchange_rate_stats["updated"])
        logger.info("Stock prices: %s updated", asset_price_stats["updated"])
        logger.info("Crypto prices: %s updated", crypto_price_stats["updated"])

        result = _make_api_call(
            "/api/snapshots/create",
            params={"snapshot_date": str(snapshot_date)},
        )

        logger.info("Snapshots created: %s", result.get("snapshots_created", 0))
        logger.info("Total value: $%s", f"{result.get('total_value_usd', 0):,.2f}")

        return result

    # Define task dependencies
    exchange_rate_stats = fetch_exchange_rates()
    asset_price_stats = fetch_asset_prices()
    crypto_price_stats = fetch_crypto_prices()
    create_snapshots(exchange_rate_stats, asset_price_stats, crypto_price_stats)


# Instantiate the DAG
dag_instance = daily_snapshot_pipeline()
