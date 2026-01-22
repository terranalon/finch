"""Binance cryptocurrency exchange parser for CSV file exports.

Handles Binance's concatenated symbol format (BTCUSDT) and
transaction types (trades, deposits, withdrawals).
"""

import csv
import logging
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from app.services.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)

# Common quote assets for symbol parsing (order matters - check longest first)
QUOTE_ASSETS = ["USDT", "BUSD", "USDC", "TUSD", "USD", "BTC", "ETH", "BNB", "EUR", "GBP"]


def parse_symbol(symbol: str) -> tuple[str, str]:
    """Parse Binance symbol into base and quote assets.

    Binance uses concatenated symbols without delimiter.
    Example: "BTCUSDT" -> ("BTC", "USDT")
    """
    symbol = symbol.upper()
    for quote in QUOTE_ASSETS:
        if symbol.endswith(quote):
            base = symbol[: -len(quote)]
            if base:  # Ensure we have a base asset
                return base, quote
    return symbol, "UNKNOWN"


class BinanceParser(BaseBrokerParser):
    """Parser for Binance cryptocurrency exchange CSV exports.

    Binance provides several export types:
    - Trade History: Buy/sell orders
    - Transaction History: Deposits and withdrawals
    - Distribution History: Staking rewards, airdrops

    Trade History CSV columns: Date(UTC), Pair, Side, Price, Executed, Amount, Fee
    """

    @classmethod
    def broker_type(cls) -> str:
        return "binance"

    @classmethod
    def broker_name(cls) -> str:
        return "Binance"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".csv"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def _parse_datetime(self, time_str: str) -> datetime | None:
        """Parse Binance timestamp formats."""
        if not time_str:
            return None

        # Binance uses various formats
        formats = [
            "%Y-%m-%d %H:%M:%S",  # Standard format
            "%Y-%m-%d %H:%M:%S.%f",  # With microseconds
            "%Y/%m/%d %H:%M:%S",  # Alternative format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse Binance timestamp: {time_str}")
        return None

    def _read_csv(self, file_content: bytes) -> tuple[list[str], list[dict]]:
        """Read CSV content and return headers and row dictionaries."""
        try:
            # Try UTF-8 first, then latin-1 as fallback
            try:
                content = file_content.decode("utf-8-sig")  # Handle BOM
            except UnicodeDecodeError:
                content = file_content.decode("latin-1")

            # Remove any empty lines at the start
            lines = [line for line in content.split("\n") if line.strip()]
            content = "\n".join(lines)

            reader = csv.DictReader(StringIO(content))
            rows = list(reader)
            headers = reader.fieldnames or []

            return headers, rows

        except csv.Error as e:
            raise ValueError(f"Failed to parse CSV: {e}") from e

    def _detect_file_type(self, headers: list[str]) -> str:
        """Detect the type of Binance export file based on headers."""
        headers_lower = [h.lower() for h in headers]

        # Trade history has Pair, Side, Price columns
        if "pair" in headers_lower and "side" in headers_lower:
            return "trades"

        # Distribution history (staking, airdrops) - check before transactions
        if any("distribution" in h for h in headers_lower):
            return "distributions"

        # Transaction history (deposits/withdrawals)
        if "operation" in headers_lower or "type" in headers_lower:
            return "transactions"

        return "unknown"

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from Binance CSV export."""
        headers, rows = self._read_csv(file_content)

        if not rows:
            raise ValueError("Empty CSV file")

        dates = []
        # Try common date column names
        date_columns = ["Date(UTC)", "date(utc)", "Date", "date", "Time", "time"]

        date_col = None
        for col in date_columns:
            if col in rows[0]:
                date_col = col
                break

        if not date_col:
            # Try to find any column with "date" or "time" in the name
            for key in rows[0].keys():
                if "date" in key.lower() or "time" in key.lower():
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
        """Parse Binance CSV file into normalized import data."""
        headers, rows = self._read_csv(file_content)

        if not rows:
            raise ValueError("Empty CSV file")

        file_type = self._detect_file_type(headers)
        logger.info(f"Parsing Binance {file_type} file with {len(rows)} rows")

        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []
        positions: list[ParsedPosition] = []

        if file_type == "trades":
            transactions = self._parse_trades(rows)
        elif file_type == "transactions":
            cash_transactions = self._parse_cash_transactions(rows)
        elif file_type == "distributions":
            dividends = self._parse_distributions(rows)
        else:
            # Try to parse as trades by default
            transactions = self._parse_trades(rows)

        # Extract date range
        start_date, end_date = self.extract_date_range(file_content)

        logger.info(
            f"Parsed Binance: {len(transactions)} trades, "
            f"{len(cash_transactions)} cash, {len(dividends)} distributions"
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            positions=positions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _parse_trades(self, rows: list[dict]) -> list[ParsedTransaction]:
        """Parse trade history rows."""
        transactions = []

        for row in rows:
            try:
                txn = self._parse_trade_row(row)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning(f"Error parsing trade row: {e}")
                continue

        return transactions

    def _parse_trade_row(self, row: dict) -> ParsedTransaction | None:
        """Parse a single trade row."""
        # Find date column
        date_str = row.get("Date(UTC)") or row.get("date(utc)") or row.get("Date", "")
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        # Get symbol/pair
        pair = row.get("Pair") or row.get("pair") or row.get("Symbol") or ""
        if not pair:
            return None

        base_asset, quote_asset = parse_symbol(pair)

        # Get side (BUY/SELL)
        side = (row.get("Side") or row.get("side") or "").upper()
        if side not in ("BUY", "SELL"):
            return None

        # Get amounts - handle various column names
        quantity = self._parse_decimal(
            row.get("Executed") or row.get("executed") or row.get("Qty") or row.get("qty")
        )
        price = self._parse_decimal(row.get("Price") or row.get("price"))
        amount = self._parse_decimal(row.get("Amount") or row.get("amount") or row.get("Total"))
        fee = self._parse_decimal(row.get("Fee") or row.get("fee") or "0")

        if quantity is None:
            return None

        # Calculate amount if not provided
        if amount is None and price is not None and quantity is not None:
            amount = price * quantity

        return ParsedTransaction(
            trade_date=dt.date(),
            symbol=base_asset,
            transaction_type="Buy" if side == "BUY" else "Sell",
            quantity=quantity,
            price_per_unit=price,
            amount=amount,
            fees=fee,
            currency=quote_asset,
            notes=f"Binance {side.lower()} - {pair}",
            raw_data=dict(row),
        )

    def _parse_cash_transactions(self, rows: list[dict]) -> list[ParsedCashTransaction]:
        """Parse transaction history (deposits/withdrawals)."""
        transactions = []

        for row in rows:
            try:
                txn = self._parse_cash_row(row)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning(f"Error parsing cash transaction row: {e}")
                continue

        return transactions

    def _parse_cash_row(self, row: dict) -> ParsedCashTransaction | None:
        """Parse a single deposit/withdrawal row."""
        date_str = row.get("Date(UTC)") or row.get("date(utc)") or row.get("Date", "")
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        # Get operation type
        operation = (
            row.get("Operation") or row.get("operation") or row.get("Type") or row.get("type") or ""
        ).lower()

        # Get coin and amount
        coin = row.get("Coin") or row.get("coin") or row.get("Asset") or row.get("asset") or ""
        amount = self._parse_decimal(row.get("Amount") or row.get("amount") or row.get("Change"))

        if not coin or amount is None:
            return None

        # Determine transaction type
        if "deposit" in operation:
            txn_type = "Deposit"
        elif "withdraw" in operation:
            txn_type = "Withdrawal"
            amount = -abs(amount)  # Ensure negative
        else:
            txn_type = operation.capitalize() or "Transfer"

        return ParsedCashTransaction(
            date=dt.date(),
            transaction_type=txn_type,
            amount=amount,
            currency=coin.upper(),
            notes=f"Binance {txn_type.lower()} - {row.get('TxId', '')}",
            raw_data=dict(row),
        )

    def _parse_distributions(self, rows: list[dict]) -> list[ParsedTransaction]:
        """Parse distribution history (staking, airdrops)."""
        dividends = []

        for row in rows:
            try:
                txn = self._parse_distribution_row(row)
                if txn:
                    dividends.append(txn)
            except Exception as e:
                logger.warning(f"Error parsing distribution row: {e}")
                continue

        return dividends

    def _parse_distribution_row(self, row: dict) -> ParsedTransaction | None:
        """Parse a single distribution row."""
        date_str = row.get("Date(UTC)") or row.get("date(utc)") or row.get("Date", "")
        dt = self._parse_datetime(date_str)
        if not dt:
            return None

        coin = row.get("Coin") or row.get("coin") or row.get("Asset") or ""
        amount = self._parse_decimal(row.get("Amount") or row.get("amount"))

        if not coin or amount is None:
            return None

        distribution_type = row.get("Distribution Type") or row.get("Type") or "Distribution"

        return ParsedTransaction(
            trade_date=dt.date(),
            symbol=coin.upper(),
            transaction_type="Distribution",
            amount=amount,
            currency=coin.upper(),
            notes=f"Binance {distribution_type}",
            raw_data=dict(row),
        )

    def _parse_decimal(self, value: str | None) -> Decimal | None:
        """Parse a string value to Decimal, handling various formats."""
        if value is None or value == "":
            return None

        try:
            # Remove currency symbols, commas, and whitespace
            clean_value = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
            return Decimal(clean_value)
        except (ValueError, ArithmeticError):
            return None
