"""Bit2C cryptocurrency exchange parser for XLSX file exports.

Handles both English and Hebrew column names and transaction types.
Supports: Buy, Sell, Deposit, Withdrawal, Fee, FeeWithdrawal, Credit.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import polars as pl

from app.services.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)
from app.services.bit2c_constants import normalize_bit2c_asset

logger = logging.getLogger(__name__)


def to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Convert a value to Decimal, returning default if None, empty, or invalid."""
    if value is None or value == "":
        return default
    return Decimal(str(value))


# English column names -> normalized names
ENGLISH_COLUMNS = {
    "id": "id",
    "created": "created",
    "accountAction": "action",
    "firstCoin": "first_coin",
    "secondCoin": "second_coin",
    "firstAmount": "first_amount",
    "secondAmount": "second_amount",
    "price": "price",
    "feeAmount": "fee_amount",
    "fee": "fee_percent",
    "balance1": "balance1",
    "balance2": "balance2",
    "ref": "ref",
    "isMaker": "is_maker",
    "Address": "address",
    "TXID": "txid",
}

# Hebrew column names -> normalized names
HEBREW_COLUMNS = {
    "מזהה": "id",
    "יצירה": "created",
    "סוג": "action",
    "מטבע 1": "first_coin",
    "מטבע 2": "second_coin",
    "סכום 1": "first_amount",
    "סכום 2": "second_amount",
    "מחיר": "price",
    "עמלה": "fee_amount",
    "עמלה %": "fee_percent",
    "יתרה 1": "balance1",
    "יתרת ש״ח\xa0": "balance2",  # Note: includes non-breaking space
    "יתרת ש״ח": "balance2",
    "אסמכתה": "ref",
    "פוזיציה": "is_maker",
    "כתובת": "address",
    "TxID": "txid",
}

# Hebrew action type to English mapping (English values pass through unchanged)
HEBREW_ACTION_MAP = {
    "קניה": "Buy",
    "מכירה": "Sell",
    "הפקדה": "Deposit",
    "משיכה": "Withdrawal",
    "עמלה": "Fee",
    "עמלת משיכה": "FeeWithdrawal",
    "זיכוי": "Credit",
}


class Bit2CParser(BaseBrokerParser):
    """Parser for Bit2C cryptocurrency exchange XLSX exports.

    Supports both English and Hebrew file formats.
    Handles: Buy, Sell, Deposit, Withdrawal, Fee, FeeWithdrawal, Credit transactions.
    """

    @classmethod
    def broker_type(cls) -> str:
        return "bit2c"

    @classmethod
    def broker_name(cls) -> str:
        return "Bit2C"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xlsx"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def _detect_language(self, columns: list[str]) -> str:
        """Detect file language based on column names."""
        hebrew_indicators = ["מזהה", "יצירה", "סוג", "מטבע"]
        for col in columns:
            if col and any(ind in str(col) for ind in hebrew_indicators):
                return "hebrew"
        return "english"

    def _read_xlsx(self, file_content: bytes) -> pl.DataFrame:
        """Read XLSX file into a Polars DataFrame with normalized column names."""
        try:
            df = pl.read_excel(BytesIO(file_content))
            if df.is_empty():
                raise ValueError("Empty file")

            language = self._detect_language(df.columns)
            column_map = HEBREW_COLUMNS if language == "hebrew" else ENGLISH_COLUMNS

            rename_map = {
                col: column_map[str(col).strip()]
                for col in df.columns
                if str(col).strip() in column_map
            }

            logger.info(f"Read Bit2C file (language: {language}, rows: {len(df)})")
            return df.rename(rename_map)

        except Exception as e:
            raise ValueError(f"Failed to read XLSX file: {e}") from e

    def _normalize_action(self, action: str) -> str:
        """Normalize action type to standard English format."""
        return HEBREW_ACTION_MAP.get(action, action)

    def _normalize_coin(self, coin: str | None) -> str | None:
        """Normalize coin name (NIS -> ILS, N/A -> None)."""
        return normalize_bit2c_asset(coin)

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from Bit2C export file."""
        df = self._read_xlsx(file_content)

        if "created" not in df.columns:
            raise ValueError("Could not find date column")

        # Filter out null dates and extract date range
        dates_col = df.select("created").drop_nulls()
        if dates_col.is_empty():
            raise ValueError("No valid dates found")

        # Convert to dates
        dates = dates_col.to_series().to_list()
        date_values = []
        for dt in dates:
            if isinstance(dt, datetime):
                date_values.append(dt.date())
            elif isinstance(dt, date):
                date_values.append(dt)

        if not date_values:
            raise ValueError("No valid dates found")

        return min(date_values), max(date_values)

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Bit2C XLSX file into normalized import data."""
        df = self._read_xlsx(file_content)

        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dates: list[date] = []

        for row in df.iter_rows(named=True):
            try:
                parsed = self._parse_row(row)
                if not parsed:
                    continue
                txn_type, data = parsed
                if txn_type == "trade":
                    # Unpack dual-entry tuple: (crypto_txn, settlement_txn)
                    crypto_txn, settlement_txn = data
                    transactions.append(crypto_txn)
                    cash_transactions.append(settlement_txn)  # Add Trade Settlement
                    dates.append(crypto_txn.trade_date)
                else:
                    # Cash transactions (Deposit, Withdrawal, Fee, etc.)
                    cash_transactions.append(data)
                    dates.append(data.date)
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")

        if not dates:
            raise ValueError("No valid transactions found")

        logger.info(
            f"Parsed Bit2C: {len(transactions)} trades, {len(cash_transactions)} cash transactions"
        )

        return BrokerImportData(
            start_date=min(dates),
            end_date=max(dates),
            transactions=transactions,
            positions=[],
            cash_transactions=cash_transactions,
            dividends=[],
        )

    def _parse_row(self, row: dict) -> tuple[str, Any] | None:
        """Parse a single row into a transaction.

        Returns:
            ("trade", (crypto_txn, settlement_txn)) for trades (dual-entry)
            ("cash", cash_txn) for cash transactions
            None if row cannot be parsed
        """
        action = row.get("action")
        if not action:
            return None

        action = self._normalize_action(str(action))

        created = row.get("created")
        if not isinstance(created, datetime):
            return None

        txn_date = created.date()
        first_coin = self._normalize_coin(row.get("first_coin"))
        first_amount = to_decimal(row.get("first_amount"))

        raw_data = {
            "id": row.get("id"),
            "ref": row.get("ref"),
            "action": action,
            "first_coin": first_coin,
            "second_coin": self._normalize_coin(row.get("second_coin")),
        }

        if action in ("Buy", "Sell"):
            return self._parse_trade(
                txn_date,
                action,
                first_coin,
                first_amount,
                to_decimal(row.get("second_amount")),
                to_decimal(row.get("price")),
                to_decimal(row.get("fee_amount"), Decimal("0")),
                raw_data,
            )

        return self._parse_cash_transaction(txn_date, action, first_coin, first_amount, raw_data)

    def _parse_trade(
        self,
        trade_date: date,
        action: str,
        first_coin: str | None,
        first_amount: Decimal | None,
        second_amount: Decimal | None,
        price: Decimal | None,
        fee_amount: Decimal,
        raw_data: dict,
    ) -> tuple[str, tuple[ParsedTransaction, ParsedCashTransaction]] | None:
        """Parse a buy/sell trade, returning BOTH crypto txn and Trade Settlement (dual-entry).

        Per CLAUDE.md Broker Integration Guidelines:
        Every trade MUST create TWO transactions:
        1. Asset Transaction: Buy/Sell on the asset holding (crypto)
        2. Trade Settlement: Cash impact on the cash holding (ILS)
        """
        if not first_coin or first_amount is None:
            return None

        is_buy = action == "Buy"
        fiat_amount = abs(second_amount) if second_amount else Decimal("0")
        quantity = abs(first_amount)

        # Settlement: Buy = negative (cash leaves), Sell = positive (cash received)
        if is_buy:
            settlement_amount = -(fiat_amount + fee_amount)
        else:
            settlement_amount = fiat_amount - fee_amount

        trade_id = raw_data.get("id", "")

        crypto_txn = ParsedTransaction(
            trade_date=trade_date,
            symbol=first_coin,
            transaction_type=action,
            quantity=quantity,
            price_per_unit=price,
            amount=fiat_amount,
            fees=fee_amount,
            currency="ILS",
            notes=f"Bit2C {action.lower()} - {trade_id}",
            raw_data=raw_data,
        )

        # Create Trade Settlement for ILS cash impact (dual-entry accounting)
        settlement_txn = ParsedCashTransaction(
            date=trade_date,
            transaction_type="Trade Settlement",
            amount=settlement_amount,
            currency="ILS",
            notes=f"Settlement for {first_coin} {action} - {trade_id}",
            raw_data=raw_data,
        )

        return ("trade", (crypto_txn, settlement_txn))

    def _parse_cash_transaction(
        self,
        txn_date: date,
        action: str,
        coin: str | None,
        amount: Decimal | None,
        raw_data: dict,
    ) -> tuple[str, ParsedCashTransaction] | None:
        """Parse a cash transaction (Deposit, Withdrawal, Fee, FeeWithdrawal, Credit)."""
        if not coin or amount is None:
            return None

        action_config = {
            "Deposit": ("Deposit", "deposit"),
            "Withdrawal": ("Withdrawal", "withdrawal"),
            "Fee": ("Fee", "custody fee"),
            "FeeWithdrawal": ("Fee", "withdrawal fee"),
            "Credit": ("Credit", "credit"),
        }

        config = action_config.get(action)
        if not config:
            return None

        txn_type, note_label = config

        return (
            "cash",
            ParsedCashTransaction(
                date=txn_date,
                transaction_type=txn_type,
                amount=amount,
                currency=coin,
                notes=f"Bit2C {note_label} - {raw_data.get('id', '')}",
                raw_data=raw_data,
            ),
        )
