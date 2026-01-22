"""TASE Data Hub API service for Israeli securities mapping.

This service provides:
1. Bulk sync of securities from TASE API to local cache
2. Local lookup of security info by Israeli security number (מספר נייר ערך)

The TASE API returns all traded securities for a given date. We cache this
locally to avoid API calls during import operations.
"""

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime

import requests
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import TASESecurity

# Lazy import of settings to avoid pydantic_settings dependency in Airflow workers
_settings = None


def _get_settings():
    """Lazy load settings to avoid import errors in environments without pydantic_settings."""
    global _settings
    if _settings is None:
        try:
            from app.config import settings

            _settings = settings
        except ImportError:
            # Fallback for environments without pydantic_settings
            _settings = None
    return _settings

logger = logging.getLogger(__name__)


@dataclass
class TASESecurityInfo:
    """Information about an Israeli security from TASE API or cache."""

    security_id: int
    symbol: str | None
    yahoo_symbol: str | None  # Symbol with .TA suffix for yfinance
    isin: str | None
    security_name: str | None
    security_name_en: str | None
    security_type_code: str | None
    company_name: str | None
    company_sector: str | None


class TASEApiService:
    """Service for interacting with TASE Data Hub API.

    Provides:
    - sync_securities_list(): Fetch all securities from TASE and update cache
    - get_security_by_number(): Local DB lookup (no API call)
    - get_yahoo_symbol(): Get yfinance-compatible symbol for Israeli security
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        """Initialize with API credentials.

        Args:
            api_key: TASE API key (defaults to settings.tase_api_key or TASE_API_KEY env var)
            base_url: TASE API base URL (defaults to settings.tase_api_url or TASE_API_URL env var)
        """
        # Try to get from parameters, then settings, then environment
        settings = _get_settings()
        if api_key:
            self.api_key = api_key
        elif settings:
            self.api_key = settings.tase_api_key
        else:
            self.api_key = os.getenv("TASE_API_KEY")

        if base_url:
            self.base_url = base_url.rstrip("/")
        elif settings:
            self.base_url = settings.tase_api_url.rstrip("/")
        else:
            self.base_url = os.getenv(
                "TASE_API_URL", "https://datahubapi.tase.co.il/api/v1"
            ).rstrip("/")

        if not self.api_key:
            logger.warning("TASE API key not configured - sync operations will fail")

    def sync_securities_list(
        self,
        db: Session,
        sync_date: date | None = None,
        language: str = "en-US",
    ) -> dict[str, int]:
        """Fetch all securities from TASE API and update local cache.

        This calls the TASE Data Hub API to get all traded securities for
        the given date, then upserts them into the tase_securities table.

        Args:
            db: Database session
            sync_date: Date to fetch securities for (defaults to today)
            language: Accept-Language header value ("en-US" or "he-IL")

        Returns:
            Dict with sync statistics: {"fetched": N, "inserted": N, "updated": N}
        """
        if not self.api_key:
            raise ValueError("TASE API key not configured")

        sync_date = sync_date or date.today()
        stats = {"fetched": 0, "inserted": 0, "updated": 0, "errors": 0}

        try:
            # Fetch securities list from TASE API
            securities = self._fetch_securities_list(sync_date, language)
            stats["fetched"] = len(securities)

            if not securities:
                logger.warning(f"No securities returned from TASE API for {sync_date}")
                return stats

            logger.info(f"Fetched {len(securities)} securities from TASE API")

            # Upsert into database
            for security_data in securities:
                try:
                    result = self._upsert_security(db, security_data)
                    if result == "inserted":
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                except Exception as e:
                    logger.error(f"Error upserting security {security_data}: {e}")
                    stats["errors"] += 1

            db.commit()
            logger.info(
                f"TASE sync complete: {stats['inserted']} inserted, "
                f"{stats['updated']} updated, {stats['errors']} errors"
            )

        except Exception as e:
            logger.error(f"Error syncing TASE securities: {e}")
            db.rollback()
            raise

        return stats

    def _fetch_securities_list(self, sync_date: date, language: str = "en-US") -> list[dict]:
        """Fetch securities list from TASE API.

        Args:
            sync_date: Date to fetch securities for
            language: Accept-Language header

        Returns:
            List of security dictionaries from API response
        """
        url = (
            f"{self.base_url}/basic-securities/trade-securities-list/"
            f"{sync_date.year}/{sync_date.month}/{sync_date.day}"
        )

        headers = {
            "accept": "application/json",
            "accept-language": language,
            "apikey": self.api_key,
        }

        logger.info(f"Fetching TASE securities list for {sync_date}")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        data = response.json()

        # Extract securities from response
        # Response format: {"tradeSecuritiesList": {"result": [...], "total": N}}
        trade_list = data.get("tradeSecuritiesList", {})
        securities = trade_list.get("result", [])

        return securities

    def _upsert_security(self, db: Session, security_data: dict) -> str:
        """Upsert a single security into the database.

        Args:
            db: Database session
            security_data: Security data from API

        Returns:
            "inserted" or "updated"
        """
        security_id = security_data.get("securityId")
        if not security_id:
            raise ValueError("Security data missing securityId")

        symbol = security_data.get("symbol")
        # Yahoo Finance uses hyphens instead of dots for Israeli fund symbols
        # e.g., TASE returns "KSM.F59" but Yahoo expects "KSM-F59.TA"
        if symbol:
            yahoo_symbol = f"{symbol.replace('.', '-')}.TA"
        else:
            yahoo_symbol = None

        # Use PostgreSQL upsert (INSERT ... ON CONFLICT DO UPDATE)
        stmt = insert(TASESecurity).values(
            security_id=security_id,
            symbol=symbol,
            yahoo_symbol=yahoo_symbol,
            isin=security_data.get("isin"),
            security_name=security_data.get("securityName"),
            security_name_en=security_data.get("securityNameEn"),
            security_type_code=security_data.get("securityFullTypeCode"),
            company_name=security_data.get("companyName"),
            company_sector=security_data.get("companySector"),
            company_sub_sector=security_data.get("companySubSector"),
            last_synced_at=datetime.now(),
        )

        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["security_id"],
            set_={
                "symbol": stmt.excluded.symbol,
                "yahoo_symbol": stmt.excluded.yahoo_symbol,
                "isin": stmt.excluded.isin,
                "security_name": stmt.excluded.security_name,
                "security_name_en": stmt.excluded.security_name_en,
                "security_type_code": stmt.excluded.security_type_code,
                "company_name": stmt.excluded.company_name,
                "company_sector": stmt.excluded.company_sector,
                "company_sub_sector": stmt.excluded.company_sub_sector,
                "last_synced_at": stmt.excluded.last_synced_at,
            },
        )

        result = db.execute(stmt)

        # Check if it was an insert or update
        # PostgreSQL returns rowcount for both, but we can check if the row existed
        return "inserted" if result.rowcount > 0 else "updated"

    def get_security_by_number(
        self, db: Session, security_number: int | str
    ) -> TASESecurityInfo | None:
        """Look up security info by Israeli security number (local DB lookup).

        This does NOT make an API call - it looks up the cached data.
        Make sure to run sync_securities_list() periodically to keep cache fresh.

        Args:
            db: Database session
            security_number: Israeli security number (מספר נייר ערך)

        Returns:
            TASESecurityInfo if found, None otherwise
        """
        security_id = int(security_number)

        stmt = select(TASESecurity).where(TASESecurity.security_id == security_id)
        result = db.execute(stmt).scalar_one_or_none()

        if not result:
            return None

        return TASESecurityInfo(
            security_id=result.security_id,
            symbol=result.symbol,
            yahoo_symbol=result.yahoo_symbol,
            isin=result.isin,
            security_name=result.security_name,
            security_name_en=result.security_name_en,
            security_type_code=result.security_type_code,
            company_name=result.company_name,
            company_sector=result.company_sector,
        )

    def get_yahoo_symbol(self, db: Session, security_number: int | str) -> str | None:
        """Get Yahoo Finance compatible symbol for Israeli security.

        Convenience method that returns just the yahoo_symbol field.

        Args:
            db: Database session
            security_number: Israeli security number

        Returns:
            Yahoo Finance symbol (e.g., "TEVA.TA") or None if not found
        """
        info = self.get_security_by_number(db, security_number)
        return info.yahoo_symbol if info else None

    def get_cache_stats(self, db: Session) -> dict:
        """Get statistics about the cached securities.

        Returns:
            Dict with cache statistics
        """
        from sqlalchemy import func

        total = db.query(func.count(TASESecurity.security_id)).scalar()
        last_sync = db.query(func.max(TASESecurity.last_synced_at)).scalar()

        return {
            "total_securities": total,
            "last_synced_at": last_sync,
        }
