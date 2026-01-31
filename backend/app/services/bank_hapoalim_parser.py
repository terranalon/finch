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
        """Extract date range from Bank Hapoalim export file."""
        raise NotImplementedError()

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Bank Hapoalim .xlsx file into normalized import data."""
        raise NotImplementedError()
