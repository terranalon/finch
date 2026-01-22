"""
Intraday Price Refresh DAG

Keeps Asset.last_fetched_price fresh for real-time dashboard display.
Fetches current prices from Yahoo Finance via the backend API.

Schedule: Every 15 minutes
- Mon-Fri: Full refresh every 15 minutes (stocks + crypto)
- Sat-Sun: Hourly refresh only (crypto only, throttled)
"""

import logging
import os
from datetime import UTC, datetime, timedelta

import requests
from airflow.sdk import dag, task
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv("/opt/airflow/backend/.env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="intraday_price_refresh",
    default_args=default_args,
    description="Refresh asset prices every 15 minutes for real-time dashboard",
    schedule="*/15 * * * *",  # Every 15 minutes, all days
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["portfolio", "prices", "intraday"],
)
def intraday_price_refresh():
    """
    DAG to refresh current asset prices for dashboard display.

    Uses smart frequency:
    - Weekdays: Run every 15 minutes (stocks + crypto active)
    - Weekends: Run only at the top of each hour (crypto only)
    """

    @task(task_id="should_run_this_cycle")
    def should_run_this_cycle() -> dict[str, bool | str]:
        """
        Determine if we should run based on day/time.

        On weekends, we throttle to hourly (only run at :00) since
        only crypto markets are active. This reduces unnecessary API calls.
        """
        now_utc = datetime.now(UTC)
        is_weekend = now_utc.weekday() >= 5  # Sat=5, Sun=6

        if is_weekend:
            # On weekends, only run at the top of each hour (minute 0-14 window)
            # This effectively gives hourly updates for crypto
            should_run = now_utc.minute < 15
            reason = "weekend_hourly" if should_run else "weekend_throttle"
        else:
            # Weekdays: always run (every 15 min)
            should_run = True
            reason = "weekday"

        logger.info(
            "Price refresh check: is_weekend=%s, minute=%d, should_run=%s, reason=%s",
            is_weekend,
            now_utc.minute,
            should_run,
            reason,
        )

        return {"should_run": should_run, "is_weekend": is_weekend, "reason": reason}

    @task(task_id="refresh_prices")
    def refresh_prices(run_status: dict[str, bool | str]) -> dict[str, int | str]:
        """
        Call backend API to refresh all asset prices.

        Args:
            run_status: Dict with should_run flag and reason

        Returns:
            Result dict with status and statistics
        """
        if not run_status.get("should_run", True):
            logger.info("Skipping price refresh: %s", run_status.get("reason"))
            return {
                "status": "skipped",
                "reason": run_status.get("reason", "unknown"),
            }

        try:
            logger.info("Starting price refresh via backend API")

            response = requests.post(
                f"{BACKEND_URL}/api/prices/update",
                params={"run_async": False},
                timeout=120,  # 2 minute timeout
            )

            if response.status_code == 200:
                data = response.json()
                stats = data.get("stats", {})
                logger.info(
                    "Price refresh complete: %d updated, %d failed, %d skipped",
                    stats.get("updated", 0),
                    stats.get("failed", 0),
                    stats.get("skipped", 0),
                )
                return {
                    "status": "success",
                    "updated": stats.get("updated", 0),
                    "failed": stats.get("failed", 0),
                    "skipped": stats.get("skipped", 0),
                }
            else:
                error_msg = response.text[:200]  # Truncate long errors
                logger.error("Price refresh API error: %d - %s", response.status_code, error_msg)
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {error_msg}",
                }

        except requests.Timeout:
            logger.exception("Price refresh timed out")
            return {"status": "failed", "error": "Request timed out after 120s"}
        except requests.RequestException as e:
            logger.exception("Network error during price refresh")
            return {"status": "failed", "error": str(e)}

    # Task flow
    run_status = should_run_this_cycle()
    refresh_prices(run_status)


# Instantiate the DAG
dag_instance = intraday_price_refresh()
