"""Bank Hapoalim broker parser for .xlsx file imports.

Handles both Hebrew and English column headers from Bank Hapoalim exports.
Prices in the export are in Agorot (Israeli cents) and are converted to ILS.
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

import polars as pl

from app.services.brokers.bank_hapoalim.constants import (
    ACTION_TYPE_MAP,
    COLUMN_INDICES,
    CURRENCY_MAP,
    ENGLISH_HEADER_NAMES,
    HEBREW_HEADER_NAMES,
)
from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
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
        df = self._read_excel(file_content)
        return self._extract_date_range_from_df(df)

    def _read_excel(self, file_content: bytes) -> pl.DataFrame:
        """Read Excel file content into a Polars DataFrame."""
        try:
            return pl.read_excel(BytesIO(file_content), has_header=False)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}") from e

    def _extract_date_range_from_df(self, df: pl.DataFrame) -> tuple[date, date]:
        """Extract date range from DataFrame row 4."""
        if len(df) < 5:
            raise ValueError("File too short - missing metadata rows")

        date_row = str(df.row(4)[0])
        logger.debug(f"Date row content: {date_row}")

        date_pattern = r"(\d{2}/\d{2}/\d{4})"
        matches = re.findall(date_pattern, date_row)

        if len(matches) < 2:
            raise ValueError(f"Could not extract date range from: {date_row}")

        start_date = datetime.strptime(matches[0], "%d/%m/%Y").date()
        end_date = datetime.strptime(matches[1], "%d/%m/%Y").date()

        return start_date, end_date

    def _detect_language(self, source: bytes | pl.DataFrame) -> bool:
        """Detect if file has English or Hebrew headers.

        Args:
            source: Either raw file bytes or a pre-parsed DataFrame.

        Returns:
            True for English, False for Hebrew.
        """
        df = self._read_excel(source) if isinstance(source, bytes) else source

        if len(df) < 6:
            raise ValueError("File too short - missing header row")

        first_col = str(df.row(5)[0])

        if first_col in ENGLISH_HEADER_NAMES or "Short security" in first_col:
            return True

        if first_col in HEBREW_HEADER_NAMES or "שם נייר" in first_col:
            return False

        raise ValueError(f"Could not detect language from header: {first_col}")

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Bank Hapoalim .xlsx file into normalized import data."""
        df = self._read_excel(file_content)

        is_english = self._detect_language(df)
        logger.info(f"Detected language: {'English' if is_english else 'Hebrew'}")

        if len(df) < 7:
            raise ValueError("File has no data rows")

        transactions: list[ParsedTransaction] = []
        dividends: list[ParsedTransaction] = []

        for row_idx in range(6, len(df)):
            row = df.row(row_idx)
            result = self._parse_row(row)
            if result is None:
                continue

            txn_type, txn = result
            if txn_type == "dividend":
                dividends.append(txn)
            else:
                transactions.append(txn)

        start_date, end_date = self._extract_date_range_from_df(df)

        logger.info(
            f"Parsed Bank Hapoalim file: {len(transactions)} transactions, "
            f"{len(dividends)} dividends"
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            positions=[],
            cash_transactions=[],
            dividends=dividends,
        )

    def _parse_row(self, row: tuple) -> tuple[str, ParsedTransaction] | None:
        """Parse a single data row into a transaction.

        Returns None if the row is empty or invalid.
        Returns tuple of (transaction_type_key, ParsedTransaction) on success.
        """
        cols = COLUMN_INDICES

        action_type_raw = str(row[cols["action_type"]] or "").strip()
        if not action_type_raw:
            return None

        action_type = ACTION_TYPE_MAP.get(action_type_raw, action_type_raw)

        date_str = str(row[cols["value_date"]] or "")
        try:
            trade_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None

        security_number = str(row[cols["security_number"]] or "").strip()
        isin = str(row[cols["isin"]] or "").strip()
        security_name = str(row[cols["short_security_name"]] or "").strip()

        quantity = self._parse_decimal(row[cols["quantity"]])
        price_agorot = self._parse_decimal(row[cols["price"]])
        # Bank Hapoalim prices are in Agorot (cents), convert to ILS
        price = price_agorot / 100 if price_agorot else Decimal("0")
        gross_value = self._parse_decimal(row[cols["gross_value"]])

        currency_raw = str(row[cols["trade_currency"]] or "").strip()
        currency = CURRENCY_MAP.get(currency_raw, currency_raw)

        israel_tax = self._parse_decimal(row[cols["israel_tax"]])
        foreign_tax = self._parse_decimal(row[cols["foreign_tax"]])
        commission = self._parse_decimal(row[cols["commission_ils"]])

        symbol = f"TASE:{security_number}" if security_number else security_name

        raw_data = {
            "security_number": security_number,
            "isin": isin,
            "security_name": security_name,
        }

        if action_type == "Dividend":
            total_tax = israel_tax + foreign_tax
            return (
                "dividend",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Dividend",
                    amount=gross_value,
                    currency=currency,
                    fees=total_tax,
                    notes=f"Dividend from {security_name}",
                    raw_data=raw_data,
                ),
            )

        if action_type == "Deposit":
            return (
                "trade",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Deposit",
                    quantity=quantity,
                    price_per_unit=price,
                    amount=gross_value,
                    currency=currency,
                    notes=f"Transfer in: {security_name}",
                    raw_data=raw_data,
                ),
            )

        return (
            "trade",
            ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type=action_type,
                quantity=quantity,
                price_per_unit=price,
                amount=abs(gross_value) if gross_value else None,
                fees=commission,
                currency=currency,
                notes=security_name,
                raw_data=raw_data,
            ),
        )

    def _parse_decimal(self, value) -> Decimal:
        """Parse a value to Decimal, returning 0 for None/empty."""
        if value is None:
            return Decimal("0")
        str_value = str(value).strip()
        if not str_value:
            return Decimal("0")
        try:
            return Decimal(str_value)
        except InvalidOperation:
            return Decimal("0")
