"""Meitav Trade broker parser for .xlsx file imports.

Handles Hebrew column names and Israeli security identification.
Prices in Meitav files are in Agorot (ILA) - 1 ILS = 100 ILA.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import polars as pl

from app.services.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)

# Agorot to Shekel conversion factor
AGOROT_TO_ILS = Decimal("100")

# Hebrew column mappings for balance.xlsx (positions)
BALANCE_COLUMNS = {
    "שם נייר": "security_name",
    "מספר נייר": "security_number",
    "סימבול": "hebrew_symbol",
    "סוג נייר": "security_type",
    "מטבע": "currency",
    "כמות נוכחית": "quantity",
    "שער": "price",  # In Agorot
    "שווי נוכחי": "market_value",  # In ILS
    "עלות": "cost_basis",  # In ILS
}

# Hebrew column mappings for transactions.xlsx
TRANSACTION_COLUMNS = {
    "תאריך": "date",
    "סוג פעולה": "action_type",
    "שם נייר": "security_name",
    "מס' נייר / סימבול": "security_number",
    "כמות": "quantity",
    "שער ביצוע": "price",  # In Agorot
    "מטבע": "currency",
    "עמלת פעולה": "commission",
    "עמלות נלוות": "additional_fees",
    "תמורה בשקלים": "proceeds_ils",
}

# Map Hebrew action types to normalized transaction types
ACTION_TYPE_MAP = {
    "קניה רצף": "Buy",
    "קניה": "Buy",
    "מכירה רצף": "Sell",
    "מכירה": "Sell",
    "דיבידנד": "Dividend",
    "העברה מזומן בשח": "Deposit",
    "העברה מזומן במטח": "Deposit",
    "משיכה": "Withdrawal",
    "ריבית בניע": "Interest",
    "ריבית": "Interest",
    'המרת מט"ח': "Forex Conversion",
}

# Map Hebrew security types to normalized asset classes
SECURITY_TYPE_MAP = {
    'מניות בש"ח': "Stock",
    "מניות": "Stock",
    "קרנות נאמנות": "MutualFund",
    "קרנות סל": "ETF",
    'אג"ח': "Bond",
    "מטבע חוץ": "Forex",
}


class MeitavParser(BaseBrokerParser):
    """Parser for Meitav Trade .xlsx broker exports.

    Supports two file types:
    - balance.xlsx: Current positions
    - transactions.xlsx: Transaction history

    All prices in Meitav files are in Agorot (ILA).
    1 Israeli Shekel (ILS) = 100 Agorot (ILA).
    """

    @classmethod
    def broker_type(cls) -> str:
        return "meitav"

    @classmethod
    def broker_name(cls) -> str:
        return "Meitav Trade"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xlsx"]

    @classmethod
    def has_api(cls) -> bool:
        return False

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from Meitav export file.

        For balance files, returns today's date (snapshot).
        For transaction files, scans all transaction dates.
        """
        try:
            df = pl.read_excel(BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}") from e

        columns = df.columns

        # Check if this is a transaction file (has date column)
        if "תאריך" in columns:
            dates = self._extract_transaction_dates(df)
            if dates:
                return min(dates), max(dates)
            # Fall back to today if no dates found
            today = date.today()
            return today, today

        # Balance file - use today's date
        today = date.today()
        return today, today

    def _extract_transaction_dates(self, df: pl.DataFrame) -> list[date]:
        """Extract all dates from transaction DataFrame."""
        dates = []
        date_col = "תאריך"

        if date_col not in df.columns:
            return dates

        for row in df.iter_rows(named=True):
            date_val = row.get(date_col)
            if date_val:
                parsed_date = self._parse_date(date_val)
                if parsed_date:
                    dates.append(parsed_date)

        return dates

    def _parse_date(self, date_val) -> date | None:
        """Parse date from various formats."""
        if isinstance(date_val, date):
            return date_val
        if isinstance(date_val, datetime):
            return date_val.date()
        if isinstance(date_val, str):
            # Try DD/MM/YYYY format (Israeli standard)
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(date_val, fmt).date()
                except ValueError:
                    continue
        return None

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Meitav .xlsx file into normalized import data."""
        try:
            df = pl.read_excel(BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}") from e

        columns = df.columns
        logger.info(f"Meitav file columns: {columns}")

        # Detect file type based on columns
        is_transaction_file = "תאריך" in columns and "סוג פעולה" in columns
        is_balance_file = "כמות נוכחית" in columns or "שווי נוכחי" in columns

        positions: list[ParsedPosition] = []
        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []

        if is_balance_file and not is_transaction_file:
            positions = self._parse_positions(df)
        elif is_transaction_file:
            txns, cash_txns, divs = self._parse_transactions(df)
            transactions = txns
            cash_transactions = cash_txns
            dividends = divs

        # Extract date range
        start_date, end_date = self.extract_date_range(file_content)

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            positions=positions,
            transactions=transactions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _parse_positions(self, df: pl.DataFrame) -> list[ParsedPosition]:
        """Parse positions from balance DataFrame."""
        positions = []

        for row in df.iter_rows(named=True):
            try:
                position = self._parse_position_row(row)
                if position:
                    positions.append(position)
            except Exception as e:
                logger.warning(f"Error parsing position row: {e}")
                continue

        logger.info(f"Parsed {len(positions)} positions from Meitav balance file")
        return positions

    def _parse_position_row(self, row: dict) -> ParsedPosition | None:
        """Parse a single position row."""
        security_number = row.get("מספר נייר")
        security_name = row.get("שם נייר", "")
        quantity = row.get("כמות נוכחית")

        # Skip rows without essential data
        if not security_number or not quantity:
            return None

        # Handle tax records (security numbers starting with 999)
        is_tax_record = str(security_number).startswith("999")

        # Get cost basis (already in ILS)
        cost_basis = row.get("עלות")
        if cost_basis is not None:
            cost_basis = Decimal(str(cost_basis))

        # Determine asset class from Hebrew security type
        security_type = row.get("סוג נייר", "").strip()
        if is_tax_record:
            # Tax records (withholding tax, tax receipts, etc.)
            asset_class = "Tax"
            symbol = f"TAX:{security_number}"
        else:
            asset_class = SECURITY_TYPE_MAP.get(security_type, "Stock")
            # Use security number as temporary symbol
            # Will be resolved to Yahoo symbol during import
            symbol = f"TASE:{security_number}"

        # Currency - normalize Hebrew currency names
        currency = self._normalize_currency(row.get("מטבע", ""))

        return ParsedPosition(
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            cost_basis=cost_basis,
            currency=currency,
            asset_class=asset_class,
            raw_data={
                "security_number": security_number,
                "security_name": security_name,
                "hebrew_symbol": row.get("סימבול"),
                "security_type": security_type,
            },
        )

    def _parse_transactions(
        self, df: pl.DataFrame
    ) -> tuple[list[ParsedTransaction], list[ParsedCashTransaction], list[ParsedTransaction]]:
        """Parse transactions from transaction DataFrame."""
        transactions = []
        cash_transactions = []
        dividends = []

        for row in df.iter_rows(named=True):
            try:
                result = self._parse_transaction_row(row)
                if result:
                    txn_type, txn = result
                    if txn_type == "trade":
                        transactions.append(txn)
                    elif txn_type == "cash":
                        cash_transactions.append(txn)
                    elif txn_type == "dividend":
                        dividends.append(txn)
            except Exception as e:
                logger.warning(f"Error parsing transaction row: {e}")
                continue

        logger.info(
            f"Parsed {len(transactions)} trades, {len(cash_transactions)} cash, "
            f"{len(dividends)} dividends from Meitav transactions"
        )
        return transactions, cash_transactions, dividends

    def _parse_transaction_row(
        self, row: dict
    ) -> tuple[str, ParsedTransaction | ParsedCashTransaction] | None:
        """Parse a single transaction row."""
        action_type = row.get("סוג פעולה", "").strip()
        if not action_type:
            return None

        # Parse date
        trade_date = self._parse_date(row.get("תאריך"))
        if not trade_date:
            return None

        # Normalize action type
        normalized_action = ACTION_TYPE_MAP.get(action_type, action_type)

        # Handle cash transactions separately
        if normalized_action in ("Deposit", "Withdrawal", "Interest", "Forex Conversion"):
            return self._parse_cash_transaction(row, trade_date, normalized_action)

        # Handle dividend
        if normalized_action == "Dividend":
            return self._parse_dividend(row, trade_date)

        # Regular trade (Buy/Sell)
        return self._parse_trade(row, trade_date, normalized_action)

    def _parse_trade(
        self, row: dict, trade_date: date, action: str
    ) -> tuple[str, ParsedTransaction] | None:
        """Parse a buy/sell transaction."""
        security_number = row.get("מס' נייר / סימבול")
        quantity = row.get("כמות")

        if not security_number or not quantity:
            return None

        # Price is in Agorot - convert to ILS
        price_agorot = row.get("שער ביצוע")
        price = None
        if price_agorot is not None:
            price = Decimal(str(price_agorot)) / AGOROT_TO_ILS

        # Commission
        commission = Decimal(str(row.get("עמלת פעולה", 0) or 0))
        additional_fees = Decimal(str(row.get("עמלות נלוות", 0) or 0))
        fees = commission + additional_fees

        # Total amount (proceeds_ils is already in ILS)
        amount = row.get("תמורה בשקלים")
        if amount is not None:
            amount = abs(Decimal(str(amount)))

        currency = self._normalize_currency(row.get("מטבע", ""))
        # Use TAX: prefix for tax codes (999...), TASE: for real securities
        is_tax_record = str(security_number).startswith("999")
        symbol = f"TAX:{security_number}" if is_tax_record else f"TASE:{security_number}"

        return (
            "trade",
            ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type=action,
                quantity=Decimal(str(quantity)),
                price_per_unit=price,
                amount=amount,
                fees=fees,
                currency=currency,
                notes=row.get("שם נייר"),
                raw_data={
                    "security_number": security_number,
                    "action_hebrew": row.get("סוג פעולה"),
                },
            ),
        )

    def _parse_dividend(self, row: dict, trade_date: date) -> tuple[str, ParsedTransaction] | None:
        """Parse a dividend transaction."""
        security_number = row.get("מס' נייר / סימבול")
        amount = row.get("תמורה בשקלים")

        if not security_number or not amount:
            return None

        currency = self._normalize_currency(row.get("מטבע", ""))
        # Use TAX: prefix for tax codes (999...), TASE: for real securities
        is_tax_record = str(security_number).startswith("999")
        symbol = f"TAX:{security_number}" if is_tax_record else f"TASE:{security_number}"

        return (
            "dividend",
            ParsedTransaction(
                trade_date=trade_date,
                symbol=symbol,
                transaction_type="Dividend",
                amount=Decimal(str(amount)),
                currency=currency,
                notes=row.get("שם נייר"),
                raw_data={"security_number": security_number},
            ),
        )

    def _parse_cash_transaction(
        self, row: dict, txn_date: date, action: str
    ) -> tuple[str, ParsedCashTransaction] | None:
        """Parse a cash transaction (deposit, withdrawal, interest)."""
        amount = row.get("תמורה בשקלים")
        if amount is None:
            return None

        currency = self._normalize_currency(row.get("מטבע", ""))

        return (
            "cash",
            ParsedCashTransaction(
                date=txn_date,
                transaction_type=action,
                amount=Decimal(str(amount)),
                currency=currency,
                notes=row.get("שם נייר"),
                raw_data={"action_hebrew": row.get("סוג פעולה")},
            ),
        )

    def _normalize_currency(self, currency_str: str) -> str:
        """Normalize Hebrew currency names to ISO codes."""
        if not currency_str:
            return "ILS"

        currency_str = currency_str.strip()

        # Map Hebrew currency names to ISO codes
        currency_map = {
            "שקל חדש": "ILS",
            "שקל": "ILS",
            "₪": "ILS",
            "דולר": "USD",
            "$": "USD",
            "אירו": "EUR",
            "€": "EUR",
        }

        # Check for matches (currency string might have trailing characters)
        for hebrew, iso in currency_map.items():
            if hebrew in currency_str:
                return iso

        # Default to ILS for Israeli broker
        return "ILS"
