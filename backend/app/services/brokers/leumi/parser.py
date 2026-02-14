"""Bank Leumi transaction file parser.

Parses SpreadsheetML XML files (.xls) exported from Bank Leumi's
online banking. Files contain transaction history in 6-month ranges.
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedTransaction,
)
from app.services.brokers.leumi.constants import (
    ACTION_TYPE_MAP,
    CURRENCY_MAP,
    SKIP_ACTION_TYPES,
    SPREADSHEET_NS,
)

logger = logging.getLogger(__name__)

AGOROT_TO_ILS = Decimal("100")
_TICKER_RE = re.compile(r"\)\s*(\w+)\s*$")


class LeumiParser(BaseBrokerParser):
    """Parser for Bank Leumi SpreadsheetML XML (.xls) files."""

    @classmethod
    def broker_type(cls) -> str:
        return "leumi"

    @classmethod
    def broker_name(cls) -> str:
        return "Bank Leumi"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xls"]

    @classmethod
    def has_api(cls) -> bool:
        return False

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        raise NotImplementedError

    def parse(self, file_content: bytes) -> BrokerImportData:
        raise NotImplementedError
