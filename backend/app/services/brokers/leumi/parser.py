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

    def _parse_xml_rows(self, file_content: bytes) -> list[dict[int, str]]:
        """Parse SpreadsheetML XML and return list of row dicts.

        Each row is a dict mapping column position (1-based) to cell value.
        Handles ss:Index attribute for sparse columns.
        """
        content = file_content.decode("utf-8").strip()
        root = ET.fromstring(content)

        ns = {"ss": SPREADSHEET_NS}
        rows: list[dict[int, str]] = []

        for row_el in root.findall(".//ss:Row", ns):
            cells: dict[int, str] = {}
            col_pos = 1
            for cell_el in row_el.findall("ss:Cell", ns):
                idx_attr = cell_el.get(f"{{{SPREADSHEET_NS}}}Index")
                if idx_attr:
                    col_pos = int(idx_attr)
                data_el = cell_el.find("ss:Data", ns)
                cells[col_pos] = data_el.text if data_el is not None else ""
                col_pos += 1
            rows.append(cells)

        return rows

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
        except ValueError:
            return None

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        rows = self._parse_xml_rows(file_content)
        dates: list[date] = []

        for row in rows[3:]:  # Skip title, metadata, header rows
            for col in (4, 5):  # execution_date, payment_date
                parsed = self._parse_date(row.get(col))
                if parsed:
                    dates = [*dates, parsed]

        if not dates:
            today = date.today()
            return today, today

        return min(dates), max(dates)

    def parse(self, file_content: bytes) -> BrokerImportData:
        raise NotImplementedError
