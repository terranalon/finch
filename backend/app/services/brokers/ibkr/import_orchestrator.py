"""IBKR import orchestration service.

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

    def __init__(self, missing_sections: list[str], required_sections: list[str]) -> None:
        self.missing_sections = missing_sections
        self.required_sections = required_sections
        super().__init__(f"Flex Query missing sections: {', '.join(missing_sections)}")


@dataclass(frozen=True)
class ImportResult:
    """Result of an import orchestration operation."""

    import_mode: Literal["full_history", "snapshot"]
    stats: dict[str, Any]
    snapshot_start: date


def _account_is_young(account_date_opened: date) -> bool:
    """Return True if the account was opened within the API history window."""
    return (date.today() - account_date_opened).days <= _MAX_API_HISTORY_DAYS


class IBKRImportOrchestrator:
    """Orchestrates IBKR import: validate, decide strategy, import."""

    @staticmethod
    def execute(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
    ) -> ImportResult:
        """Fetch XML, validate sections, and import based on account age.

        Returns an ImportResult with the chosen mode and import stats.

        Raises:
            MissingFlexSectionsError: If required Flex Query sections are absent.
            RuntimeError: If the XML fetch or parse fails.
        """
        xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)
        if not xml_data:
            raise RuntimeError("Failed to fetch Flex Query report. Check your token and query ID.")

        root = IBKRParser.parse_xml(xml_data)
        if root is None:
            raise RuntimeError("Failed to parse Flex Query XML response.")

        missing = IBKRParser.validate_required_sections(root)
        if missing:
            raise MissingFlexSectionsError(missing, IBKRParser.get_required_section_names())

        account_info = IBKRParser.extract_account_info(root)

        if account_info and _account_is_young(account_info.date_opened):
            logger.info(
                "Account %d opened %s -- using full history import",
                account_id,
                account_info.date_opened,
            )
            stats = IBKRFlexImportService.import_all(
                db,
                account_id,
                flex_token,
                flex_query_id,
                start_date=account_info.date_opened,
                pre_fetched_root=root,
            )
            import_mode: Literal["full_history", "snapshot"] = "full_history"
            snapshot_start = account_info.date_opened
        else:
            logger.info(
                "Account %d too old or missing date -- using snapshot import",
                account_id,
            )
            stats = IBKRSyntheticImportService.import_snapshot(
                db, account_id, flex_token, flex_query_id, pre_fetched_root=root
            )
            import_mode = "snapshot"
            snapshot_start = date.today()

        if stats.get("status") == "failed":
            errors = stats.get("errors", ["Unknown error"])
            raise RuntimeError(f"Import failed: {errors}")

        return ImportResult(
            import_mode=import_mode,
            stats=stats,
            snapshot_start=snapshot_start,
        )
