"""Bank Hapoalim broker parser for .xlsx file imports.

Handles both Hebrew and English column headers from Bank Hapoalim exports.
Prices are in full currency units (not Agorot like Meitav).
"""

import logging
from datetime import date
from decimal import Decimal
from io import BytesIO

import polars as pl

from app.services.bank_hapoalim_constants import (
    ACTION_TYPE_MAP,
    COLUMN_INDICES,
    CURRENCY_MAP,
    ENGLISH_HEADER_NAMES,
    HEBREW_HEADER_NAMES,
)
from app.services.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)


class BankHapoalimParser(BaseBrokerParser):
    """Parser for Bank Hapoalim .xlsx broker exports."""

    @classmethod
    def broker_type(cls) -> str:
        return "bank_hapoalim"

    @classmethod
    def broker_name(cls) -> str:
        return "Bank Hapoalim"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xlsx"]

    @classmethod
    def has_api(cls) -> bool:
        return False

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from Bank Hapoalim export file.

        The date range is in metadata row 4 (0-indexed):
        - English: "Dates included: DD/MM/YYYY to DD/MM/YYYY"
        - Hebrew: "תאריכים הנכללים בתקופה: DD/MM/YYYY עד DD/MM/YYYY"
        """
        import re
        from datetime import datetime

        try:
            df = pl.read_excel(BytesIO(file_content), has_header=False)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}") from e

        if len(df) < 5:
            raise ValueError("File too short - missing metadata rows")

        # Row 4 (0-indexed) contains the date range
        date_row = str(df.row(4)[0])
        logger.debug(f"Date row content: {date_row}")

        # Extract dates using regex (DD/MM/YYYY format)
        date_pattern = r"(\d{2}/\d{2}/\d{4})"
        matches = re.findall(date_pattern, date_row)

        if len(matches) < 2:
            raise ValueError(f"Could not extract date range from: {date_row}")

        start_str, end_str = matches[0], matches[1]

        # Parse DD/MM/YYYY format
        start_date = datetime.strptime(start_str, "%d/%m/%Y").date()
        end_date = datetime.strptime(end_str, "%d/%m/%Y").date()

        return start_date, end_date

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Bank Hapoalim .xlsx file into normalized import data."""
        raise NotImplementedError()
