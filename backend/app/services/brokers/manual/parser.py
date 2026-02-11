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

TRADE_TYPES = {"Buy", "Sell"}
DIVIDEND_TYPES = {"Dividend", "Interest", "Staking"}
CASH_TYPES = {"Deposit", "Withdrawal"}

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
        rows = self._read_rows(file_content)
        if not rows:
            raise ValueError("Empty file: no data rows found")

        dates = self._collect_dates(rows)
        if not dates:
            raise ValueError("No valid dates found in file")

        return min(dates), max(dates)

    def parse(self, file_content: bytes) -> BrokerImportData:
        rows = self._read_rows(file_content)
        if not rows:
            raise ValueError("Empty file: no data rows found")

        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []
        dates: list[date] = []

        for i, row in enumerate(rows, start=2):
            try:
                result = self._parse_row(row, i)
                if result is None:
                    continue
            except ValueError as e:
                logger.warning("Row %d: %s", i, e)
                continue

            category, record = result

            if category == "transaction":
                transactions.append(record)
                dates.append(record.trade_date)
            elif category == "cash":
                cash_transactions.append(record)
                dates.append(record.date)
            elif category == "dividend":
                dividends.append(record)
                dates.append(record.trade_date)

        if not dates:
            today = date.today()
            return BrokerImportData(start_date=today, end_date=today)

        return BrokerImportData(
            start_date=min(dates),
            end_date=max(dates),
            transactions=transactions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    # -- Private helpers -------------------------------------------------------

    def _read_rows(self, file_content: bytes) -> list[dict]:
        if not file_content:
            raise ValueError("Empty file")
        if file_content[:4] == b"PK\x03\x04":
            return self._read_xlsx(file_content)
        return self._read_csv(file_content)

    def _read_csv(self, file_content: bytes) -> list[dict]:
        try:
            content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            content = file_content.decode("latin-1")

        reader = csv.DictReader(StringIO(content))
        rows = list(reader)

        if not rows:
            raise ValueError("Empty CSV file")

        self._validate_columns(set(rows[0].keys()))
        return rows

    def _read_xlsx(self, file_content: bytes) -> list[dict]:
        df = pl.read_excel(BytesIO(file_content))

        if df.is_empty():
            raise ValueError("Empty XLSX file")

        self._validate_columns(set(df.columns))

        return [
            {k: str(v) if v is not None else "" for k, v in row.items()}
            for row in df.iter_rows(named=True)
        ]

    def _validate_columns(self, columns: set[str]) -> None:
        normalized = {c.strip().lower() for c in columns}
        missing = REQUIRED_COLUMNS - normalized
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    def _normalize_row(self, row: dict) -> dict:
        normalized = {}
        for k, v in row.items():
            if isinstance(v, str):
                normalized[k.strip().lower()] = v.strip()
            elif v is not None:
                normalized[k.strip().lower()] = str(v)
            else:
                normalized[k.strip().lower()] = ""
        return normalized

    def _parse_row(
        self, row: dict, row_num: int
    ) -> tuple[str, ParsedTransaction | ParsedCashTransaction] | None:
        row = self._normalize_row(row)

        txn_type = row.get("type", "").title()
        if txn_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid type '{txn_type}'. Must be one of: {', '.join(sorted(VALID_TYPES))}"
            )

        for field in TYPE_REQUIRED_FIELDS[txn_type]:
            if not row.get(field, ""):
                raise ValueError(f"'{field}' is required for type '{txn_type}'")

        trade_date = date.fromisoformat(row["date"])
        symbol = row["symbol"].upper()
        currency = row["currency"].upper()
        fees = self._parse_decimal(row.get("fees")) or Decimal("0")
        notes = row.get("notes", "") or None

        quantity = self._parse_decimal(row.get("quantity"))
        price = self._parse_decimal(row.get("price"))
        amount = self._parse_decimal(row.get("amount"))

        if txn_type in CASH_TYPES:
            return "cash", ParsedCashTransaction(
                date=trade_date,
                transaction_type=txn_type,
                amount=amount if txn_type == "Deposit" else -abs(amount),
                currency=currency,
                fees=fees,
                notes=notes,
            )

        if txn_type in DIVIDEND_TYPES:
            return "dividend", ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type=txn_type,
                quantity=quantity,
                amount=amount,
                currency=currency,
                fees=fees,
                notes=notes,
            )

        # Buy / Sell
        if amount is None and quantity is not None and price is not None:
            amount = quantity * price

        return "transaction", ParsedTransaction(
            trade_date=trade_date,
            symbol=symbol,
            transaction_type=txn_type,
            quantity=quantity,
            price_per_unit=price,
            amount=amount,
            currency=currency,
            fees=fees,
            notes=notes,
        )

    @staticmethod
    def _parse_decimal(value: str | None) -> Decimal | None:
        if not value or not value.strip():
            return None
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None

    @staticmethod
    def _collect_dates(rows: list[dict]) -> list[date]:
        dates = []
        for row in rows:
            raw_date = row.get("date", "").strip()
            if not raw_date:
                continue
            try:
                dates.append(date.fromisoformat(raw_date))
            except ValueError:
                continue
        return dates
