"""KuCoin cryptocurrency exchange parser for CSV file exports.

Handles KuCoin's dash-separated symbol format (BTC-USDT) and multiple
CSV export types: trade history, deposit/withdrawal, staking/bonus.
"""

import csv
import logging
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)
from app.services.brokers.kucoin.constants import parse_symbol

logger = logging.getLogger(__name__)


class KuCoinParser(BaseBrokerParser):
    """Parser for KuCoin cryptocurrency exchange CSV exports.

    Supports three CSV export types, auto-detected from headers:
    - Trade History: buy/sell orders with symbol, side, price, size, funds, fee
    - Deposit/Withdrawal: deposits and withdrawals with coin, amount, type, status
    - Staking/Bonus: staking rewards with currency, amount, remarks
    """

    @classmethod
    def broker_type(cls) -> str:
        return "kucoin"

    @classmethod
    def broker_name(cls) -> str:
        return "KuCoin"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".csv"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def _parse_datetime(self, time_str: str) -> datetime | None:
        """Parse KuCoin timestamp formats."""
        if not time_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with milliseconds (trade history)
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 without milliseconds
            "%Y-%m-%d %H:%M:%S",  # Standard format (deposit/withdrawal)
            "%Y-%m-%d %H:%M:%S.%f",  # With microseconds
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning("Could not parse KuCoin timestamp: %s", time_str)
        return None

    def _read_csv(self, file_content: bytes) -> tuple[list[str], list[dict]]:
        """Read CSV content and return headers and row dictionaries."""
        try:
            try:
                content = file_content.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = file_content.decode("latin-1")

            lines = [line for line in content.split("\n") if line.strip()]
            content = "\n".join(lines)

            reader = csv.DictReader(StringIO(content))
            rows = list(reader)
            headers: list[str] = list(reader.fieldnames or [])

            return headers, rows

        except csv.Error as e:
            raise ValueError(f"Failed to parse CSV: {e}") from e

    def _detect_file_type(self, headers: list[str]) -> str:
        """Detect the type of KuCoin export file based on headers."""
        headers_lower = [h.lower() for h in headers]

        if "symbol" in headers_lower and "side" in headers_lower:
            return "trades"

        if "type" in headers_lower and ("coin" in headers_lower or "status" in headers_lower):
            return "deposits"

        if "currency" in headers_lower and "remarks" in headers_lower:
            return "staking"

        return "unknown"

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from KuCoin CSV export."""
        headers, rows = self._read_csv(file_content)

        if not rows:
            raise ValueError("Empty CSV file")

        dates: list[date] = []
        date_columns = [
            "tradeCreatedAt",
            "Time",
            "time",
            "createAt",
            "Date",
            "date",
        ]

        date_col = None
        for col in date_columns:
            if col in rows[0]:
                date_col = col
                break

        if not date_col:
            for key in rows[0]:
                if "date" in key.lower() or "time" in key.lower() or "created" in key.lower():
                    date_col = key
                    break

        if not date_col:
            raise ValueError("Could not find date column in CSV")

        for row in rows:
            dt = self._parse_datetime(row.get(date_col, ""))
            if dt:
                dates.append(dt.date())

        if not dates:
            raise ValueError("No valid dates found in file")

        return min(dates), max(dates)

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse KuCoin CSV file into normalized import data."""
        headers, rows = self._read_csv(file_content)

        if not rows:
            raise ValueError("Empty CSV file")

        file_type = self._detect_file_type(headers)
        logger.info("Parsing KuCoin %s file with %d rows", file_type, len(rows))

        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []

        if file_type == "trades":
            transactions = self._parse_trades(rows)
        elif file_type == "deposits":
            cash_transactions = self._parse_cash_transactions(rows)
        elif file_type == "staking":
            dividends = self._parse_staking(rows)
        else:
            transactions = self._parse_trades(rows)

        start_date, end_date = self.extract_date_range(file_content)

        logger.info(
            "Parsed KuCoin: %d trades, %d cash, %d staking",
            len(transactions),
            len(cash_transactions),
            len(dividends),
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _parse_trades(self, rows: list[dict]) -> list[ParsedTransaction]:
        """Parse trade history rows."""
        transactions: list[ParsedTransaction] = []

        for row in rows:
            try:
                txn = self._parse_trade_row(row)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning("Error parsing KuCoin trade row: %s", e)

        return transactions

    def _parse_trade_row(self, row: dict) -> ParsedTransaction | None:
        """Parse a single trade row."""
        date_str = row.get("tradeCreatedAt") or row.get("Time") or row.get("time", "")
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        symbol_str = row.get("symbol") or row.get("Symbol") or ""
        if not symbol_str:
            return None

        base_asset, quote_asset = parse_symbol(symbol_str)

        side = (row.get("side") or row.get("Side") or "").lower()
        if side not in ("buy", "sell"):
            return None

        quantity = self._parse_decimal(row.get("size") or row.get("Size"))
        price = self._parse_decimal(row.get("price") or row.get("Price"))
        amount = self._parse_decimal(row.get("funds") or row.get("Funds") or row.get("Amount"))
        fee = self._parse_decimal(row.get("fee") or row.get("Fee") or "0")

        if quantity is None:
            return None

        if amount is None and price is not None:
            amount = price * quantity

        order_id = row.get("orderId") or row.get("OrderId") or ""

        return ParsedTransaction(
            trade_date=dt.date(),
            symbol=base_asset,
            transaction_type="Buy" if side == "buy" else "Sell",
            quantity=quantity,
            price_per_unit=price,
            amount=amount,
            fees=fee or Decimal("0"),
            currency=quote_asset,
            external_transaction_id=order_id,
            notes=f"KuCoin {side} - {symbol_str}",
            raw_data=dict(row),
        )

    def _parse_cash_transactions(self, rows: list[dict]) -> list[ParsedCashTransaction]:
        """Parse deposit/withdrawal history rows."""
        transactions: list[ParsedCashTransaction] = []

        for row in rows:
            try:
                txn = self._parse_cash_row(row)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning("Error parsing KuCoin cash row: %s", e)

        return transactions

    def _parse_cash_row(self, row: dict) -> ParsedCashTransaction | None:
        """Parse a single deposit/withdrawal row."""
        date_str = row.get("Time") or row.get("time") or row.get("createAt") or ""
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        # Filter by status -- only completed transactions
        status = (row.get("Status") or row.get("status") or "").lower()
        if status and status not in ("completed", "success"):
            return None

        coin = (row.get("Coin") or row.get("coin") or row.get("Currency") or "").upper()
        amount = self._parse_decimal(row.get("Amount") or row.get("amount"))
        if not coin or amount is None:
            return None

        txn_type = (row.get("Type") or row.get("type") or "").lower()

        if "deposit" in txn_type:
            transaction_type = "Deposit"
        elif "withdraw" in txn_type:
            transaction_type = "Withdrawal"
            amount = -abs(amount)
        else:
            transaction_type = txn_type.capitalize() or "Transfer"

        fee = self._parse_decimal(row.get("Fee") or row.get("fee") or "0")

        return ParsedCashTransaction(
            date=dt.date(),
            transaction_type=transaction_type,
            amount=amount,
            currency=coin,
            fees=fee or Decimal("0"),
            notes=f"KuCoin {transaction_type.lower()}",
            raw_data=dict(row),
        )

    def _parse_staking(self, rows: list[dict]) -> list[ParsedTransaction]:
        """Parse staking/bonus history rows."""
        dividends: list[ParsedTransaction] = []

        for row in rows:
            try:
                txn = self._parse_staking_row(row)
                if txn:
                    dividends.append(txn)
            except Exception as e:
                logger.warning("Error parsing KuCoin staking row: %s", e)

        return dividends

    def _parse_staking_row(self, row: dict) -> ParsedTransaction | None:
        """Parse a single staking/bonus row."""
        date_str = row.get("Time") or row.get("time") or ""
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        currency = (row.get("Currency") or row.get("currency") or row.get("Coin") or "").upper()
        amount = self._parse_decimal(row.get("Amount") or row.get("amount"))
        if not currency or amount is None:
            return None

        remarks = row.get("Remarks") or row.get("remarks") or "Staking"

        return ParsedTransaction(
            trade_date=dt.date(),
            symbol=currency,
            transaction_type="Staking",
            amount=amount,
            currency=currency,
            notes=f"KuCoin {remarks}",
            raw_data=dict(row),
        )

    def _parse_decimal(self, value: str | None) -> Decimal | None:
        """Parse a string value to Decimal, handling various formats."""
        if value is None or value == "":
            return None

        try:
            clean_value = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
            return Decimal(clean_value)
        except (ValueError, ArithmeticError):
            return None
