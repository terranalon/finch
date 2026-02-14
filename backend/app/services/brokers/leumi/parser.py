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
                cells[col_pos] = (data_el.text or "") if data_el is not None else ""
                col_pos += 1
            rows = [*rows, cells]

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
        return self._date_range_from_rows(rows)

    def _date_range_from_rows(self, rows: list[dict[int, str]]) -> tuple[date, date]:
        """Extract min/max dates from pre-parsed rows.

        Scans execution_date (col 4) and payment_date (col 5) across
        all data rows (skipping title, metadata, and header rows).
        """
        dates: list[date] = []

        for row in rows[3:]:  # Skip title, metadata, header rows
            for col in (4, 5):  # execution_date, payment_date
                parsed = self._parse_date(row.get(col))
                if parsed:
                    dates = [*dates, parsed]

        if not dates:
            raise ValueError("No valid dates found in Leumi file")

        return min(dates), max(dates)

    @staticmethod
    def _parse_decimal(value: str | None) -> Decimal:
        if not value:
            return Decimal("0")
        try:
            return Decimal(value.strip().replace(",", ""))
        except InvalidOperation:
            return Decimal("0")

    @staticmethod
    def _normalize_currency(currency_str: str | None) -> str:
        if not currency_str:
            return "ILS"
        stripped = currency_str.strip()
        for hebrew, iso in CURRENCY_MAP.items():
            if hebrew in stripped:
                return iso
        return "ILS"

    @staticmethod
    def _resolve_symbol(security_number: str, name: str, currency: str) -> str:
        """Resolve security to a symbol for import.

        ILS securities -> TASE:{number}
        USD securities -> extracted English ticker from name, fallback to TASE:{number}
        """
        if currency == "USD":
            match = _TICKER_RE.search(name)
            if match:
                return match.group(1)
        return f"TASE:{security_number}"

    def _parse_row(self, row: dict[int, str]) -> tuple[str, ParsedTransaction] | None:
        """Parse a single data row into a categorized ParsedTransaction.

        Returns tuple of (category, transaction) where category is "trade"
        or "dividend", or None if the row should be skipped.
        """
        action_raw = (row.get(3) or "").strip()
        if not action_raw or action_raw in SKIP_ACTION_TYPES:
            return None

        action_type = ACTION_TYPE_MAP.get(action_raw)
        if not action_type:
            logger.warning("Unknown Leumi action type: %s", action_raw)
            return None

        security_number = (row.get(1) or "").strip()
        name = (row.get(2) or "").strip()
        exec_date = self._parse_date(row.get(4))
        pay_date = self._parse_date(row.get(5))
        quantity = self._parse_decimal(row.get(6))
        price_raw = self._parse_decimal(row.get(7))
        amount_raw = self._parse_decimal(row.get(8))
        commission = self._parse_decimal(row.get(9))
        tax = self._parse_decimal(row.get(10))
        currency = self._normalize_currency(row.get(11))

        trade_date = exec_date or pay_date
        if not trade_date:
            return None

        symbol = self._resolve_symbol(security_number, name, currency)

        # ILS prices are in Agorot (divide by 100); USD prices are direct
        price = price_raw / AGOROT_TO_ILS if currency == "ILS" and price_raw else price_raw

        raw_data = {
            "security_number": security_number,
            "name": name,
            "action_type": action_raw,
        }

        if action_type == "Dividend":
            return (
                "dividend",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Dividend",
                    amount=amount_raw,
                    currency=currency,
                    fees=abs(tax),
                    notes=name,
                    raw_data=raw_data,
                ),
            )

        if action_type == "Tax":
            return (
                "trade",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Tax",
                    amount=abs(tax),
                    currency=currency,
                    notes=name,
                    raw_data=raw_data,
                ),
            )

        if action_type == "Bonus":
            return (
                "trade",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Bonus",
                    quantity=quantity,
                    price_per_unit=price,
                    amount=Decimal("0"),
                    currency=currency,
                    notes=name,
                    raw_data=raw_data,
                ),
            )

        # Buy / Sell
        return (
            "trade",
            ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type=action_type,
                quantity=abs(quantity) if quantity else None,
                price_per_unit=price if price else None,
                amount=abs(amount_raw) if amount_raw else None,
                fees=abs(commission) + abs(tax),
                currency=currency,
                notes=name,
                raw_data=raw_data,
            ),
        )

    def parse(self, file_content: bytes) -> BrokerImportData:
        rows = self._parse_xml_rows(file_content)

        transactions: list[ParsedTransaction] = []
        dividends: list[ParsedTransaction] = []

        for row in rows[3:]:
            result = self._parse_row(row)
            if result is None:
                continue
            category, txn = result
            if category == "dividend":
                dividends = [*dividends, txn]
            else:
                transactions = [*transactions, txn]

        start_date, end_date = self._date_range_from_rows(rows)

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            dividends=dividends,
        )
