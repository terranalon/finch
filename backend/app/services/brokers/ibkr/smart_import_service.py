"""IBKR smart import orchestration service.

Fetches a Flex Query report once, validates required sections, determines
the import strategy based on account age, and delegates to the appropriate
import service (full history or synthetic snapshot).
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService

logger = logging.getLogger(__name__)

_MAX_API_HISTORY_DAYS = 365


class MissingFlexSectionsError(Exception):
    """Raised when the Flex Query is missing required sections."""

    def __init__(self, missing_sections: list[str]) -> None:
        self.missing_sections = missing_sections
        super().__init__(f"Flex Query missing sections: {', '.join(missing_sections)}")


@dataclass(frozen=True)
class SmartImportResult:
    """Result of a smart import operation."""

    import_mode: Literal["full_history", "snapshot"]
    stats: dict[str, Any]
    snapshot_start: date


class IBKRSmartImportService:
    """Orchestrates IBKR smart import: validate, decide strategy, import."""

    @staticmethod
    def execute(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
    ) -> SmartImportResult:
        """Fetch XML, validate sections, and import based on account age.

        Returns a SmartImportResult with the chosen mode and import stats.

        Raises:
            MissingFlexSectionsError: If required Flex Query sections are absent.
            RuntimeError: If the XML fetch or parse fails.
        """
        # Step 1: Fetch XML once
        xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)
        if not xml_data:
            raise RuntimeError("Failed to fetch Flex Query report. Check your token and query ID.")

        root = IBKRParser.parse_xml(xml_data)
        if root is None:
            raise RuntimeError("Failed to parse Flex Query XML response.")

        # Step 2: Validate required sections
        missing = IBKRParser.validate_required_sections(root)
        if missing:
            raise MissingFlexSectionsError(missing)

        # Step 3: Determine import mode based on account age
        account_info = IBKRParser.extract_account_info(root)

        if account_info and (date.today() - account_info.date_opened).days <= _MAX_API_HISTORY_DAYS:
            import_mode: Literal["full_history", "snapshot"] = "full_history"
            snapshot_start = account_info.date_opened
            logger.info(
                "Account %d opened %s -- using full history import",
                account_id,
                snapshot_start,
            )
            stats = IBKRFlexImportService.import_all(
                db,
                account_id,
                flex_token,
                flex_query_id,
                start_date=account_info.date_opened,
                pre_fetched_root=root,
            )
        else:
            import_mode = "snapshot"
            snapshot_start = date.today()
            logger.info(
                "Account %d too old or missing date -- using snapshot import",
                account_id,
            )
            stats = IBKRSyntheticImportService.import_snapshot(
                db, account_id, flex_token, flex_query_id, pre_fetched_root=root
            )

        if stats.get("status") == "failed":
            raise RuntimeError(f"Import failed: {stats.get('errors', ['Unknown error'])}")

        return SmartImportResult(
            import_mode=import_mode,
            stats=stats,
            snapshot_start=snapshot_start,
        )
