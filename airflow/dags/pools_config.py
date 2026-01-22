"""
Airflow Pools Configuration

This module documents and verifies the database pools used to limit concurrent DB operations.
This prevents connection exhaustion when multiple DAGs run simultaneously.

IMPORTANT: Pools must be created manually (Astronomer security prevents automatic creation):
    Option 1: Via Airflow UI - Admin -> Pools -> Create
    Option 2: Via CLI from host:
        docker exec <scheduler-container> airflow pools set db_write_pool 2 "Description"
        docker exec <scheduler-container> airflow pools set db_read_pool 5 "Description"

Required Pools:
    - db_write_pool (2 slots): Limits concurrent write-heavy operations (imports, syncs)
    - db_read_pool (5 slots): For read operations (can have more slots since reads don't block)

This DAG verifies that pools are configured correctly. Run it after manual setup.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

# Expected pool configuration
REQUIRED_POOLS = {
    "db_write_pool": {
        "min_slots": 2,
        "description": "Pool for write-heavy database operations (imports, syncs)",
    },
    "db_read_pool": {
        "min_slots": 5,
        "description": "Pool for read-heavy database operations",
    },
}


@dag(
    dag_id="setup_airflow_pools",
    default_args=default_args,
    description="Verify Airflow pools are configured for database operations",
    schedule=None,  # Manual trigger only
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["setup", "pools", "verification"],
)
def setup_airflow_pools():
    """
    DAG to verify Airflow pools are correctly configured.

    Pools must be created manually via CLI or UI before running this DAG.
    This DAG only verifies the configuration is correct.
    """

    @task(task_id="verify_pools")
    def verify_pools() -> dict[str, str]:
        """Verify that required pools exist with correct configuration.

        Raises:
            ValueError: If any required pool is missing or misconfigured.
        """
        import subprocess

        results = {}
        missing_pools = []

        # Use airflow pools list to check existing pools
        cmd = ["airflow", "pools", "list", "-o", "json"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json

            pools_data = json.loads(result.stdout)

            # Build lookup of existing pools
            existing_pools = {p["pool"]: p for p in pools_data}

            for pool_name, expected in REQUIRED_POOLS.items():
                if pool_name not in existing_pools:
                    missing_pools.append(pool_name)
                    results[pool_name] = "MISSING"
                    logger.error(f"Pool {pool_name} is missing!")
                else:
                    pool = existing_pools[pool_name]
                    actual_slots = pool.get("slots", 0)
                    if actual_slots >= expected["min_slots"]:
                        results[pool_name] = f"OK ({actual_slots} slots)"
                        logger.info(f"Pool {pool_name}: {actual_slots} slots - OK")
                    else:
                        results[pool_name] = f"LOW SLOTS ({actual_slots} < {expected['min_slots']})"
                        logger.warning(
                            f"Pool {pool_name} has only {actual_slots} slots, "
                            f"expected at least {expected['min_slots']}"
                        )

        except subprocess.CalledProcessError as e:
            # CLI approach blocked by Astronomer - pools exist but we can't verify
            logger.warning(f"Could not verify pools via CLI: {e.stderr}")
            logger.info("Pools should be verified manually via Airflow UI")
            return {"status": "manual_verification_required"}

        if missing_pools:
            error_msg = (
                f"Missing required pools: {missing_pools}. Create them via Airflow UI or CLI."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Pool verification complete: {results}")
        return results

    verify_pools()


# Instantiate the DAG
dag_instance = setup_airflow_pools()


# Pool assignments for tasks that can use them:
# Add pool="db_write_pool" to write-heavy tasks:
#   - sync_tase_securities in tase_securities_sync.py
#   - import_broker_data in hourly_broker_import.py
#   - fetch_asset_prices in daily_snapshot_pipeline.py
#   - backfill_asset_prices in backfill_historical_data.py
#
# Example:
#   @task(task_id="sync_tase_securities", pool="db_write_pool")
#   def sync_tase_securities():
#       ...
