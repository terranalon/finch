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

    def _detect_language(self, file_content: bytes) -> bool:
        """Detect if file has English or Hebrew headers.

        Returns True for English, False for Hebrew.
        Header row is at row 5 (0-indexed).
        """
        df = pl.read_excel(BytesIO(file_content), has_header=False)

        if len(df) < 6:
            raise ValueError("File too short - missing header row")

        # Header row is row 5 (0-indexed)
        header_row = df.row(5)
        first_col = str(header_row[0])

        # Check for English header
        if first_col in ENGLISH_HEADER_NAMES or "Short security" in first_col:
            return True

        # Check for Hebrew header
        if first_col in HEBREW_HEADER_NAMES or "שם נייר" in first_col:
            return False

        raise ValueError(f"Could not detect language from header: {first_col}")

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Bank Hapoalim .xlsx file into normalized import data."""
        from datetime import datetime

        try:
            df = pl.read_excel(BytesIO(file_content), has_header=False)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}") from e

        # Detect language (currently unused, but kept for future localization)
        is_english = self._detect_language(file_content)
        logger.info(f"Detected language: {'English' if is_english else 'Hebrew'}")

        # Data starts at row 6 (0-indexed), header is row 5
        if len(df) < 7:
            raise ValueError("File has no data rows")

        transactions: list[ParsedTransaction] = []
        dividends: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []

        cols = COLUMN_INDICES

        # Process each data row (starting from row 6)
        for row_idx in range(6, len(df)):
            row = df.row(row_idx)

            try:
                result = self._parse_row(row, cols)
                if result:
                    txn_type, txn = result
                    if txn_type == "dividend":
                        dividends.append(txn)
                    else:
                        transactions.append(txn)
            except Exception as e:
                logger.warning(f"Error parsing row {row_idx}: {e}")
                continue

        # Extract date range
        start_date, end_date = self.extract_date_range(file_content)

        logger.info(
            f"Parsed Bank Hapoalim file: {len(transactions)} transactions, "
            f"{len(dividends)} dividends"
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            positions=[],
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _parse_row(
        self, row: tuple, cols: dict
    ) -> tuple[str, ParsedTransaction] | None:
        """Parse a single data row into a transaction."""
        from datetime import datetime

        # Get action type
        action_type_raw = str(row[cols["action_type"]] or "").strip()
        if not action_type_raw:
            return None

        action_type = ACTION_TYPE_MAP.get(action_type_raw, action_type_raw)

        # Parse date (DD/MM/YYYY)
        date_str = str(row[cols["value_date"]] or "")
        try:
            trade_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None

        # Get security info
        security_number = str(row[cols["security_number"]] or "").strip()
        isin = str(row[cols["isin"]] or "").strip()
        security_name = str(row[cols["short_security_name"]] or "").strip()

        # Get amounts
        quantity = self._parse_decimal(row[cols["quantity"]])
        price = self._parse_decimal(row[cols["price"]])
        gross_value = self._parse_decimal(row[cols["gross_value"]])

        # Get currency
        currency_raw = str(row[cols["trade_currency"]] or "").strip()
        currency = CURRENCY_MAP.get(currency_raw, currency_raw)

        # Get taxes and commission
        israel_tax = self._parse_decimal(row[cols["israel_tax"]])
        foreign_tax = self._parse_decimal(row[cols["foreign_tax"]])
        commission = self._parse_decimal(row[cols["commission_ils"]])

        # Build symbol from security number
        symbol = f"TASE:{security_number}" if security_number else security_name

        # Determine amount based on transaction type
        amount = abs(gross_value) if gross_value else None

        if action_type == "Dividend":
            total_tax = (israel_tax or Decimal("0")) + (foreign_tax or Decimal("0"))
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
                    raw_data={
                        "security_number": security_number,
                        "isin": isin,
                        "security_name": security_name,
                    },
                ),
            )

        if action_type == "Deposit":
            # Transfer in - treat as deposit with cost basis
            return (
                "deposit",
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=symbol,
                    transaction_type="Deposit",
                    quantity=quantity,
                    price_per_unit=price,
                    amount=gross_value,
                    currency=currency,
                    notes=f"Transfer in: {security_name}",
                    raw_data={
                        "security_number": security_number,
                        "isin": isin,
                        "security_name": security_name,
                    },
                ),
            )

        # Buy or Sell
        return (
            "trade",
            ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type=action_type,
                quantity=quantity,
                price_per_unit=price,
                amount=amount,
                fees=commission or Decimal("0"),
                currency=currency,
                notes=security_name,
                raw_data={
                    "security_number": security_number,
                    "isin": isin,
                    "security_name": security_name,
                },
            ),
        )

    def _parse_decimal(self, value) -> Decimal:
        """Parse a value to Decimal, returning 0 for None/empty."""
        if value is None or value == "" or str(value).strip() == "":
            return Decimal("0")
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")
