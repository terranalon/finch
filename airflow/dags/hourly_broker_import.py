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

logger = logging.getLogger(__name__)

load_dotenv("/opt/airflow/backend/.env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


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
        """Get accounts with broker API connections from backend.

        Calls the backend API to get all accounts that have broker API
        credentials configured. The backend is the single source of truth
        for which brokers support API imports and credential validation.

        Returns:
            List of dicts with account_id and broker_type keys.

        Raises:
            AirflowException: If API call fails after retries.
        """
        auth_helper = get_auth_helper()
        url = f"{BACKEND_URL}/api/brokers/api-connections"

        try:
            response = requests.get(
                url,
                headers=auth_helper.get_auth_headers(),
                timeout=30,
            )

            # Retry once on 401 (token might be stale)
            if response.status_code == 401:
                logger.warning("Got 401, refreshing token and retrying...")
                auth_helper.force_refresh()
                response = requests.get(
                    url,
                    headers=auth_helper.get_auth_headers(),
                    timeout=30,
                )

            response.raise_for_status()
            accounts = response.json()
            logger.info("Found %d account-broker pairs for import", len(accounts))
            return accounts

        except requests.RequestException as e:
            logger.exception("Failed to fetch API connections from backend")
            raise AirflowException(f"Failed to fetch API connections: {e}") from e

    @task(task_id="import_broker_data", pool="db_write_pool")
    def import_broker_data(account_info: dict) -> dict:
        """Import data for a single account from its broker API.

        Args:
            account_info: Dict with account_id and broker_type keys.

        Returns:
            Import result with status and statistics.

        Raises:
            AirflowException: On import failure (ensures task fails loudly).
        """
        account_id = account_info["account_id"]
        broker_type = account_info["broker_type"]

        logger.info("Importing %s data for account %d", broker_type, account_id)

        auth_helper = get_auth_helper()
        url = f"{BACKEND_URL}/api/brokers/{broker_type}/import/{account_id}"

        try:
            response = requests.post(
                url,
                headers=auth_helper.get_auth_headers(),
                timeout=300,
            )

            # Retry once on 401 (token might be stale)
            if response.status_code == 401:
                logger.warning("Got 401, refreshing token and retrying...")
                auth_helper.force_refresh()
                response = requests.post(
                    url,
                    headers=auth_helper.get_auth_headers(),
                    timeout=300,
                )

            if response.status_code == 200:
                stats = response.json().get("stats", {})
                logger.info(
                    "%s import completed for account %d: %s",
                    broker_type,
                    account_id,
                    stats,
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
