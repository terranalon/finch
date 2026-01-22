"""
TASE Securities Sync DAG

Syncs Israeli securities data from TASE Data Hub API to local cache.
This enables mapping of Israeli security numbers (מספר נייר ערך) to
Yahoo Finance compatible symbols for Meitav Trade imports.

Schedule: Daily at 20:00 UTC (staggered to avoid overlap with other DAGs)
- TASE updates their data at end of trading day (~17:30 Israel time)
- We sync at 20:00 UTC to ensure fresh data is available
"""

import logging
import os
import sys
from datetime import datetime, timedelta

import requests
from airflow.sdk import dag, task

# Add dags folder to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from queries import BATCH_UPSERT_TASE_SECURITIES, GET_TASE_CACHE_STATS
from shared_db import get_engine

logger = logging.getLogger(__name__)

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="tase_securities_sync",
    default_args=default_args,
    description="Sync Israeli securities from TASE Data Hub API",
    schedule="0 20 * * *",  # 20:00 UTC - staggered to avoid overlap with daily_snapshot (21:30)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["portfolio", "tase", "israeli_securities"],
)
def tase_securities_sync():
    """
    DAG to sync TASE securities list for Israeli security mapping.

    This maintains a local cache of all TASE-traded securities,
    enabling fast lookup during Meitav file imports without
    making API calls during import operations.
    """

    @task(task_id="sync_tase_securities", pool="db_write_pool")
    def sync_tase_securities() -> dict[str, int | str]:
        """
        Fetch all securities from TASE API and update local cache.

        Uses batch INSERT to minimize database lock time and prevent UI blocking.

        Returns:
            Dict with sync statistics
        """
        from datetime import date

        from sqlalchemy import text

        # Get config directly from environment
        tase_api_key = os.getenv("TASE_API_KEY")
        tase_api_url = os.getenv("TASE_API_URL", "https://datahubapi.tase.co.il/api/v1").rstrip("/")

        # Check if API key is configured
        if not tase_api_key:
            logger.error("TASE API key not configured - skipping sync")
            return {"status": "skipped", "reason": "TASE_API_KEY not configured"}

        stats = {"fetched": 0, "inserted": 0, "updated": 0, "errors": 0}

        try:
            # Fetch securities from TASE API
            sync_date = date.today()
            url = f"{tase_api_url}/basic-securities/trade-securities-list/{sync_date.year}/{sync_date.month}/{sync_date.day}"
            headers = {
                "accept": "application/json",
                "accept-language": "en-US",
                "apikey": tase_api_key,
            }

            logger.info(f"Fetching TASE securities for {sync_date}")
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()

            data = response.json()
            securities = data.get("tradeSecuritiesList", {}).get("result", [])
            stats["fetched"] = len(securities)

            if not securities:
                logger.warning(f"No securities returned from TASE API for {sync_date}")
                return {"status": "success", **stats}

            logger.info(f"Fetched {len(securities)} securities from TASE API")

            # Collect all securities data first (no DB operations yet)
            batch_params = []
            for sec in securities:
                security_id = sec.get("securityId")
                if not security_id:
                    continue

                symbol = sec.get("symbol")
                yahoo_symbol = f"{symbol.replace('.', '-')}.TA" if symbol else None

                batch_params.append(
                    {
                        "security_id": security_id,
                        "symbol": symbol,
                        "yahoo_symbol": yahoo_symbol,
                        "isin": sec.get("isin"),
                        "security_name": sec.get("securityName"),
                        "security_name_en": sec.get("securityNameEn"),
                        "security_type_code": sec.get("securityFullTypeCode"),
                        "company_name": sec.get("companyName"),
                        "company_sector": sec.get("companySector"),
                        "company_sub_sector": sec.get("companySubSector"),
                    }
                )

            # Batch insert all securities in a single transaction
            # This minimizes lock time compared to individual inserts
            engine = get_engine()
            with engine.connect() as conn:
                try:
                    # Use executemany for batch upsert - single round-trip to DB
                    conn.execute(text(BATCH_UPSERT_TASE_SECURITIES), batch_params)
                    conn.commit()
                    stats["inserted"] = len(batch_params)
                    logger.info(f"Batch upserted {len(batch_params)} securities")
                except Exception as e:
                    logger.error(f"Batch upsert failed: {e}")
                    conn.rollback()
                    stats["errors"] = len(batch_params)
                    raise

            logger.info(f"TASE sync complete: {stats}")
            return {"status": "success", **stats}

        except Exception as e:
            logger.exception("TASE sync failed")
            return {"status": "failed", "error": str(e)}

    @task(task_id="report_cache_stats")
    def report_cache_stats(sync_result: dict[str, int | str]) -> dict[str, int | str]:
        """
        Report statistics about the TASE securities cache.

        Uses shared database connection pool to prevent connection exhaustion.

        Args:
            sync_result: Result from sync task

        Returns:
            Dict with cache statistics
        """
        from sqlalchemy import text

        try:
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute(text(GET_TASE_CACHE_STATS)).fetchone()

                total_securities = result[0] if result else 0
                last_synced_at = result[1] if result else None

            logger.info(
                "TASE cache stats: total_securities=%d, last_synced=%s",
                total_securities,
                last_synced_at,
            )

            return {
                "sync_status": sync_result.get("status", "unknown"),
                "total_securities": total_securities,
                "last_synced_at": str(last_synced_at) if last_synced_at else None,
            }

        except Exception as e:
            logger.exception("Failed to get cache stats")
            return {
                "sync_status": sync_result.get("status", "unknown"),
                "error": str(e),
            }

    # Task flow
    sync_result = sync_tase_securities()
    report_cache_stats(sync_result)


# Instantiate the DAG
dag_instance = tase_securities_sync()
