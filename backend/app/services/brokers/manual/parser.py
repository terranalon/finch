"""Manual import parser for user-provided CSV/XLSX files."""

import csv
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import polars as pl

from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"date", "type", "symbol", "currency"}

VALID_TYPES = {"Buy", "Sell", "Dividend", "Deposit", "Withdrawal", "Interest", "Staking"}

TYPE_REQUIRED_FIELDS: dict[str, set[str]] = {
    "Buy": {"quantity", "price"},
    "Sell": {"quantity", "price"},
    "Dividend": {"amount"},
    "Interest": {"amount"},
    "Staking": {"quantity"},
    "Deposit": {"amount"},
    "Withdrawal": {"amount"},
}


class ManualParser(BaseBrokerParser):
    """Parser for manually created CSV/XLSX import files."""

    @classmethod
    def broker_type(cls) -> str:
        return "manual"

    @classmethod
    def broker_name(cls) -> str:
        return "Manual Import"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".csv", ".xlsx"]

    @classmethod
    def has_api(cls) -> bool:
        return False

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        raise NotImplementedError

    def parse(self, file_content: bytes) -> BrokerImportData:
        raise NotImplementedError
