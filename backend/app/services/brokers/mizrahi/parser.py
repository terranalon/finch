"""Mizrahi Tefahot broker parser for .xls file imports.

Mizrahi Tefahot exports .xls files that are actually UTF-16 LE encoded HTML
containing two tables: a header table with account info and a data table
with securities transactions. Prices for ILS securities are in Agorot.
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedTransaction,
)
from app.services.brokers.mizrahi.constants import (
    ACTION_TYPE_MAP,
    CURRENCY_CODE_MAP,
    TAX_CODE_PREFIX,
)

logger = logging.getLogger(__name__)

AGOROT_TO_ILS = Decimal("100")

# Matches a closing paren followed by an English ticker at end of name.
# Used by Israeli brokers whose exports include tickers like "NVIDIA CORP) NVDA".
_TICKER_RE = re.compile(r"\)\s*(\w+)\s*$")


class _TableExtractor(HTMLParser):
    """Extract rows from HTML tables.

    Returns a list of tables, where each table is a list of rows,
    and each row is a list of cell text values.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: str = ""
        self._in_cell: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._current_table = []
        elif tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._current_cell = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self.tables = [*self.tables, self._current_table]
        elif tag == "tr":
            self._current_table = [*self._current_table, self._current_row]
        elif tag in ("td", "th"):
            self._current_row = [*self._current_row, self._current_cell.strip()]
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell += data


class MizrahiParser(BaseBrokerParser):
    """Parser for Mizrahi Tefahot .xls (HTML) broker exports."""

    @classmethod
    def broker_type(cls) -> str:
        return "mizrahi"

    @classmethod
    def broker_name(cls) -> str:
        return "Mizrahi Tefahot"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xls"]

    @classmethod
    def has_api(cls) -> bool:
        return False

    @staticmethod
    def _decode_content(file_content: bytes) -> str:
        """Decode UTF-16 LE content, stripping BOM if present."""
        text = file_content.decode("utf-16-le")
        if text.startswith("\ufeff"):
            text = text[1:]
        return text

    def _parse_html_tables(self, file_content: bytes) -> tuple[str, list[dict[str, str]]]:
        """Parse HTML tables from file content.

        Returns:
            Tuple of (account_info_string, list_of_row_dicts).
            Each row dict maps Hebrew column names to cell values.
        """
        html = self._decode_content(file_content)

        extractor = _TableExtractor()
        extractor.feed(html)

        if len(extractor.tables) < 2:
            raise ValueError(
                "Mizrahi file must contain at least 2 tables (header and transactions)"
            )

        # Table 0: header with account info
        header_table = extractor.tables[0]
        account_info = " ".join(cell for row in header_table for cell in row if cell)

        # Table 1: transaction data
        data_table = extractor.tables[1]
        if len(data_table) < 2:
            raise ValueError("Transaction table has no data rows")

        # First row is the header
        headers = [h.strip() for h in data_table[0]]

        # Remaining rows are data, mapped to header names
        rows: list[dict[str, str]] = []
        for raw_row in data_table[1:]:
            row_dict: dict[str, str] = {}
            for i, value in enumerate(raw_row):
                if i < len(headers) and headers[i]:
                    row_dict[headers[i]] = value
            rows = [*rows, row_dict]

        return account_info, rows

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        """Parse DD/MM/YY date string to date object."""
        if not date_str or not date_str.strip():
            return None
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%y").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_decimal(value: str | None) -> Decimal:
        """Parse a numeric string with commas to Decimal."""
        if not value or not value.strip():
            return Decimal("0")
        try:
            return Decimal(value.strip().replace(",", ""))
        except InvalidOperation:
            return Decimal("0")

    @staticmethod
    def _is_tax_code(security_number: str) -> bool:
        """Check if security number is a tax code (starts with 999)."""
        return security_number.startswith(TAX_CODE_PREFIX)

    @staticmethod
    def _resolve_symbol(security_number: str, name: str, currency: str) -> str:
        """Resolve security to a symbol for import.

        ILS securities -> TASE:{number}
        USD securities -> extracted English ticker from name, fallback to TASE:{number}
        Tax codes -> TAX:{number}
        """
        if not security_number:
            return ""
        if MizrahiParser._is_tax_code(security_number):
            return f"TAX:{security_number}"
        if currency == "USD":
            match = _TICKER_RE.search(name)
            if match:
                return match.group(1)
        return f"TASE:{security_number}"

    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction | None:
        """Parse a single data row into a ParsedTransaction.

        Returns None if the row should be skipped (empty or unknown action type).
        """
        action_raw = row.get("סוג פעולה", "").strip()
        if not action_raw:
            return None

        action_type = ACTION_TYPE_MAP.get(action_raw)
        if not action_type:
            logger.warning("Unknown Mizrahi action type: %s", action_raw)
            return None

        trade_date = self._parse_date(row.get("תאריך פעולה"))
        if not trade_date:
            return None

        return self._build_transaction(row, action_type, action_raw, trade_date)

    def _build_transaction(
        self, row: dict[str, str], action_type: str, action_raw: str, trade_date: date
    ) -> ParsedTransaction:
        """Build a ParsedTransaction from validated row data."""
        security_number = row.get("מספר נייר", "").strip()
        security_name = row.get("שם נייר", "").strip()
        currency_code = row.get("קוד מטבע", "").strip()
        currency = CURRENCY_CODE_MAP.get(currency_code, "ILS")

        quantity_raw = self._parse_decimal(row.get("כמות"))
        price_raw = self._parse_decimal(row.get("שער פעולה"))
        commission = self._parse_decimal(row.get("עמלה/הוצ' סליקה"))
        correspondent_fee = self._parse_decimal(row.get("עמלת קורספונדנט"))
        net_cash = self._parse_decimal(row.get("כספי-נטו"))

        # ILS prices are in Agorot (divide by 100); USD prices are direct
        price = price_raw / AGOROT_TO_ILS if currency == "ILS" and price_raw else price_raw
        fees = abs(commission) + abs(correspondent_fee)
        symbol = self._resolve_symbol(security_number, security_name, currency)
        amount = abs(net_cash) if net_cash else None

        return ParsedTransaction(
            trade_date=trade_date,
            symbol=symbol,
            transaction_type=action_type,
            quantity=abs(quantity_raw) if quantity_raw else None,
            price_per_unit=price if price else None,
            amount=amount,
            fees=fees,
            currency=currency,
            notes=security_name,
            raw_data={
                "security_number": security_number,
                "security_name": security_name,
                "action_type": action_raw,
                "currency_code": currency_code,
            },
        )

    def _date_range_from_rows(self, rows: list[dict[str, str]]) -> tuple[date, date]:
        """Extract min/max trade dates from pre-parsed rows."""
        dates: list[date] = []
        for row in rows:
            parsed = self._parse_date(row.get("תאריך פעולה"))
            if parsed:
                dates = [*dates, parsed]

        if not dates:
            raise ValueError("No valid dates found in Mizrahi file")

        return min(dates), max(dates)

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from transaction dates."""
        _header, rows = self._parse_html_tables(file_content)
        return self._date_range_from_rows(rows)

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Mizrahi .xls file into normalized import data."""
        _header, rows = self._parse_html_tables(file_content)

        transactions: list[ParsedTransaction] = []
        for row in rows:
            txn = self._parse_row(row)
            if txn is not None:
                transactions = [*transactions, txn]

        start_date, end_date = self._date_range_from_rows(rows)

        logger.info("Parsed %d transactions from Mizrahi file", len(transactions))

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
        )
