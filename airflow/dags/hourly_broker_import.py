"""Hourly Broker Data Import DAG.

Orchestrates hourly data imports from broker APIs (IBKR, Binance, Kraken, Bit2C).
Schedule: Every hour at minute 5 (staggered to avoid overlap with other DAGs)

Authentication: Uses service account JWT for API authentication.
"""

import logging
import os
from datetime import datetime, timedelta

import requests
from airflow.exceptions import AirflowException
from airflow.sdk import dag, task
from auth_helper import get_auth_helper
from dotenv import load_dotenv
from queries import GET_ACCOUNTS_WITH_BROKER_API
from shared_db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

load_dotenv("/opt/airflow/backend/.env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")

# Broker configuration: maps broker_type to (credential_keys, endpoint_path, stats_key)
BROKER_CONFIG = {
    "ibkr": {
        "cred_keys": ("flex_token", "flex_query_id"),
        "endpoint": "/api/brokers/ibkr/import",
        "stats_key": "stats",
    },
    "binance": {
        "cred_keys": ("api_key", "api_secret"),
        "endpoint": "/api/brokers/binance/import",
        "stats_key": "stats",
    },
    "kraken": {
        "cred_keys": ("api_key", "api_secret"),
        "endpoint": "/api/brokers/kraken/import",
        "stats_key": "stats",
    },
    "bit2c": {
        "cred_keys": ("api_key", "api_secret"),
        "endpoint": "/api/brokers/bit2c/import",
        "stats_key": "stats",
    },
}

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


def _has_broker_credentials(meta_data: dict, broker_type: str) -> bool:
    """Check if account has valid credentials for a broker type."""
    config = BROKER_CONFIG.get(broker_type)
    if not config:
        return False
    broker_data = meta_data.get(broker_type, {})
    return all(broker_data.get(key) for key in config["cred_keys"])


def _extract_error_message(response: requests.Response) -> str:
    """Extract error message from API response."""
    try:
        return response.json().get("detail", response.text)
    except (ValueError, KeyError):
        return response.text


@dag(
    dag_id="hourly_broker_import",
    default_args=default_args,
    description="Hourly data import from broker APIs (IBKR, Binance, etc.)",
    schedule="5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["broker", "import", "hourly"],
)
def hourly_broker_import():
    """DAG to import data from broker APIs for all configured accounts."""

    @task(task_id="get_active_accounts")
    def get_active_accounts() -> list[dict]:
        """Get all accounts with broker API credentials configured."""
        db = SessionLocal()
        try:
            result = db.execute(text(GET_ACCOUNTS_WITH_BROKER_API))
            accounts = []

            for row in result:
                account_id, meta_data = row[0], row[1]
                if not meta_data:
                    continue

                for broker_type in BROKER_CONFIG:
                    if _has_broker_credentials(meta_data, broker_type):
                        accounts.append({"account_id": account_id, "broker_type": broker_type})
                        logger.info("Found %s credentials for account %d", broker_type, account_id)

            logger.info("Found %d accounts with broker API credentials", len(accounts))
            return accounts

        finally:
            db.close()

    @task(task_id="import_broker_data", pool="db_write_pool")
    def import_broker_data(account_info: dict) -> dict:
        """Import data for a single account from its broker API.

        Raises:
            AirflowException: On import failure (ensures task fails loudly)
        """
        account_id = account_info["account_id"]
        broker_type = account_info["broker_type"]

        logger.info("Importing %s data for account %d", broker_type, account_id)

        config = BROKER_CONFIG.get(broker_type)
        if not config:
            logger.warning("Unknown broker type: %s", broker_type)
            return {
                "account_id": account_id,
                "broker_type": broker_type,
                "status": "skipped",
                "reason": f"Unknown broker type: {broker_type}",
            }

        auth_helper = get_auth_helper()
        url = f"{BACKEND_URL}{config['endpoint']}/{account_id}"

        try:
            response = requests.post(url, headers=auth_helper.get_auth_headers(), timeout=300)

            # Retry once on 401 (token might be stale)
            if response.status_code == 401:
                logger.warning("Got 401, refreshing token and retrying...")
                auth_helper.force_refresh()
                response = requests.post(url, headers=auth_helper.get_auth_headers(), timeout=300)

            if response.status_code == 200:
                stats = response.json().get(config["stats_key"], {})
                logger.info(
                    "%s import completed for account %d: %s", broker_type, account_id, stats
                )
                return {
                    "account_id": account_id,
                    "broker_type": broker_type,
                    "status": "success",
                    "statistics": stats,
                }

            # Non-200 response: fail loudly
            error_msg = _extract_error_message(response)
            logger.error(
                "%s import failed for account %d (HTTP %d): %s",
                broker_type,
                account_id,
                response.status_code,
                error_msg,
            )
            raise AirflowException(
                f"{broker_type} import failed for account {account_id}: "
                f"HTTP {response.status_code} - {error_msg}"
            )

        except requests.RequestException as e:
            logger.exception("Network error importing data for account %d", account_id)
            raise AirflowException(
                f"Network error importing {broker_type} data for account {account_id}: {e}"
            ) from e

    @task(task_id="aggregate_results")
    def aggregate_results(results: list[dict]) -> dict:
        """Aggregate import results for logging and monitoring.

        Args:
            results: List of import results from all accounts

        Returns:
            Summary statistics
        """
        summary = {
            "total_accounts": len(results),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_transactions": 0,
            "total_positions": 0,
            "errors": [],
        }

        for result in results:
            status = result.get("status", "unknown")
            if status == "success":
                summary["successful"] += 1
                stats = result.get("statistics", {})
                summary["total_transactions"] += stats.get("transactions_imported", 0)
                summary["total_positions"] += stats.get("positions_imported", 0)
            elif status == "failed":
                summary["failed"] += 1
                summary["errors"].append(
                    {
                        "account_id": result.get("account_id"),
                        "error": result.get("error"),
                    }
                )
            else:
                summary["skipped"] += 1

        logger.info(
            "Hourly broker import complete: %d successful, %d failed, %d skipped",
            summary["successful"],
            summary["failed"],
            summary["skipped"],
        )

        if summary["errors"]:
            logger.warning("Import errors: %s", summary["errors"])

        return summary

    # Task flow
    accounts = get_active_accounts()
    # Use dynamic task mapping for parallel imports
    import_results = import_broker_data.expand(account_info=accounts)
    aggregate_results(import_results)


# Instantiate the DAG
dag_instance = hourly_broker_import()
