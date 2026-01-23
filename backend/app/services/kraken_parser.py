"""Kraken cryptocurrency exchange parser for CSV ledger exports.

Handles Kraken's non-standard asset naming (XXBT, ZUSD, etc.) and
transaction types (trades, deposits, withdrawals, staking rewards).
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
from app.services.kraken_constants import FIAT_CURRENCIES, normalize_kraken_asset

logger = logging.getLogger(__name__)


class KrakenParser(BaseBrokerParser):
    """Parser for Kraken cryptocurrency exchange CSV exports.

    Kraken provides ledger exports that include:
    - Deposits and withdrawals
    - Trade executions (buy/sell pairs with same refid)
    - Staking rewards
    - Transfers and adjustments

    CSV columns: txid, refid, time, type, subtype, aclass, asset, amount, fee, balance
    """

    @classmethod
    def broker_type(cls) -> str:
        return "kraken"

    @classmethod
    def broker_name(cls) -> str:
        return "Kraken"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".csv"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def _normalize_asset(self, asset: str) -> str:
        """Normalize Kraken asset names to standard symbols."""
        return normalize_kraken_asset(asset)

    def _parse_datetime(self, time_str: str) -> datetime | None:
        """Parse Kraken timestamp format."""
        if not time_str:
            return None

        # Kraken uses format: "2024-01-15 10:30:00"
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse Kraken timestamp: {time_str}")
        return None

    def _read_csv(self, file_content: bytes) -> list[dict]:
        """Read CSV content and return list of row dictionaries."""
        try:
            # Try UTF-8 first, then latin-1 as fallback
            try:
                content = file_content.decode("utf-8")
            except UnicodeDecodeError:
                content = file_content.decode("latin-1")

            reader = csv.DictReader(StringIO(content))
            rows = list(reader)

            # Validate required columns
            if rows:
                required = {"txid", "time", "type", "asset", "amount"}
                actual = set(rows[0].keys())
                missing = required - actual
                if missing:
                    raise ValueError(f"Missing required columns: {missing}")

            return rows

        except csv.Error as e:
            raise ValueError(f"Failed to parse CSV: {e}") from e

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from Kraken CSV export."""
        try:
            rows = self._read_csv(file_content)
        except Exception as e:
            raise ValueError(f"Failed to parse Kraken CSV: {e}") from e

        if not rows:
            raise ValueError("Empty CSV file")

        dates = []
        for row in rows:
            dt = self._parse_datetime(row.get("time", ""))
            if dt:
                dates.append(dt.date())

        if not dates:
            raise ValueError("No valid dates found in file")

        return min(dates), max(dates)

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse Kraken CSV file into normalized import data."""
        rows = self._read_csv(file_content)

        if not rows:
            raise ValueError("Empty CSV file")

        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []
        positions: list[ParsedPosition] = []

        # Group rows by refid for trades (trades have matching buy/sell entries)
        trades_by_refid: dict[str, list[dict]] = {}

        for row in rows:
            txn_type = row.get("type", "").lower()
            refid = row.get("refid", "")

            if txn_type == "trade" and refid:
                if refid not in trades_by_refid:
                    trades_by_refid[refid] = []
                trades_by_refid[refid].append(row)
            elif txn_type in (
                "deposit",
                "withdrawal",
                "staking",
                "transfer",
                "adjustment",
                "earn",
            ):
                parsed = self._parse_non_trade_entry(row, txn_type)
                if parsed:
                    category, data = parsed
                    if category == "cash":
                        cash_transactions.append(data)
                    elif category == "dividend":
                        dividends.append(data)
                    else:  # crypto_deposit, crypto_withdrawal, transfer
                        transactions.append(data)

        # Process grouped trades (returns both crypto txns and trade settlements)
        for refid, trade_rows in trades_by_refid.items():
            parsed_trades, trade_settlements = self._parse_trade_group(trade_rows)
            transactions.extend(parsed_trades)
            cash_transactions.extend(trade_settlements)

        # Extract date range
        start_date, end_date = self.extract_date_range(file_content)

        logger.info(
            f"Parsed Kraken ledger: {len(transactions)} trades, "
            f"{len(cash_transactions)} cash, {len(dividends)} staking rewards"
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            positions=positions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _parse_non_trade_entry(
        self, row: dict, entry_type: str
    ) -> tuple[str, ParsedTransaction | ParsedCashTransaction] | None:
        """Parse a single non-trade ledger entry.

        Trade entries are handled by _parse_trade_group() which groups
        crypto+fiat sides together.

        Returns:
            Tuple of (category, parsed_data) where category is one of:
            - "cash": Fiat deposit/withdrawal -> ParsedCashTransaction
            - "crypto_deposit": Crypto deposit -> ParsedTransaction
            - "crypto_withdrawal": Crypto withdrawal -> ParsedTransaction
            - "dividend": Staking reward -> ParsedTransaction
            - "transfer": Internal transfer -> ParsedTransaction
        """
        dt = self._parse_datetime(row.get("time", ""))
        if not dt:
            return None

        amount_str = row.get("amount", "")
        if not amount_str:
            return None

        entry_date = dt.date()
        asset = self._normalize_asset(row.get("asset", ""))
        amount = Decimal(amount_str)
        fee = Decimal(row.get("fee", "0") or "0")
        refid = row.get("refid", "")

        if entry_type == "deposit":
            if asset in FIAT_CURRENCIES:
                net_amount = amount - fee
                return (
                    "cash",
                    ParsedCashTransaction(
                        date=entry_date,
                        transaction_type="Deposit",
                        amount=net_amount,
                        currency=asset,
                        fees=fee,
                        notes=f"Kraken deposit - {refid}",
                        raw_data=dict(row),
                    ),
                )
            # Crypto deposit - creates holding quantity
            # Note: Price lookup for cost basis is not available in CSV parser
            # (API client uses CoinGecko for this)
            return (
                "crypto_deposit",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Deposit",
                    quantity=amount,
                    price_per_unit=None,
                    amount=amount,
                    currency="USD",
                    notes=f"Kraken crypto deposit - {refid}",
                    raw_data=dict(row),
                ),
            )

        if entry_type == "withdrawal":
            # Net amount = withdrawal amount - fee (both are negative impact)
            net_amount = amount - fee
            if asset in FIAT_CURRENCIES:
                return (
                    "cash",
                    ParsedCashTransaction(
                        date=entry_date,
                        transaction_type="Withdrawal",
                        amount=net_amount,
                        currency=asset,
                        fees=fee,
                        notes=f"Kraken withdrawal - {refid}",
                        raw_data=dict(row),
                    ),
                )
            # Crypto withdrawal - reduces holding quantity
            return (
                "crypto_withdrawal",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Withdrawal",
                    quantity=net_amount,
                    price_per_unit=None,
                    amount=net_amount,
                    currency="USD",
                    notes=f"Kraken crypto withdrawal - {refid}",
                    raw_data=dict(row),
                ),
            )

        if entry_type == "staking":
            net_quantity = amount - fee
            return (
                "dividend",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Staking",
                    quantity=net_quantity,
                    amount=net_quantity,
                    fees=fee,
                    currency="USD",
                    notes=f"Kraken staking reward - {refid}",
                    raw_data=dict(row),
                ),
            )

        if entry_type in ("transfer", "adjustment"):
            subtype = row.get("subtype", "")
            return (
                "transfer",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Transfer",
                    quantity=amount,
                    price_per_unit=None,
                    amount=amount,
                    currency="USD",
                    notes=f"Kraken transfer ({subtype}) - {refid}",
                    raw_data=dict(row),
                ),
            )

        if entry_type == "earn":
            subtype = row.get("subtype", "")

            # Earn rewards are staking dividends
            if subtype == "reward":
                net_quantity = amount - fee
                return (
                    "dividend",
                    ParsedTransaction(
                        trade_date=entry_date,
                        symbol=asset,
                        transaction_type="Staking",
                        quantity=net_quantity,
                        amount=net_quantity,
                        fees=fee,
                        currency="USD",
                        notes=f"Kraken earn reward - {refid}",
                        raw_data=dict(row),
                    ),
                )

            # Allocation/autoallocation - internal transfers to/from earn wallet
            return (
                "transfer",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Transfer",
                    quantity=amount,
                    price_per_unit=None,
                    amount=amount,
                    currency="USD",
                    notes=f"Kraken earn ({subtype}) - {refid}",
                    raw_data=dict(row),
                ),
            )

        return None

    def _parse_trade_group(
        self, rows: list[dict]
    ) -> tuple[list[ParsedTransaction], list[ParsedCashTransaction]]:
        """Parse a group of trade rows with same refid.

        Kraken trades come in pairs: one negative (sold) and one positive (bought).
        Example: Buy BTC with USD creates:
        - ZUSD: -500.25 (sold USD)
        - XXBT: +0.01 (bought BTC)

        For fiat-to-crypto trades, this creates:
        1. A crypto transaction with quantity adjusted for fees
        2. A Trade Settlement cash transaction for dual-entry accounting

        Fee handling:
        - Buy: quantity = crypto_received - crypto_fee (fee reduces what you get)
        - Sell: quantity = crypto_sold + crypto_fee (fee adds to what you give up)

        Returns:
            Tuple of (crypto transactions, trade settlement cash transactions)
        """
        if not rows:
            return [], []

        dt = self._parse_datetime(rows[0].get("time", ""))
        if not dt:
            return [], []

        trade_date = dt.date()

        # Separate crypto and fiat entries
        crypto_entry = None
        fiat_entry = None
        crypto_entries = []

        for row in rows:
            asset = self._normalize_asset(row.get("asset", ""))
            if asset in FIAT_CURRENCIES:
                fiat_entry = row
            else:
                crypto_entry = row
                crypto_entries.append(row)

        # Crypto-to-crypto trade: both sides are crypto (no fiat involved)
        if fiat_entry is None:
            if len(crypto_entries) == 2:
                return self._parse_crypto_to_crypto_trade(crypto_entries, trade_date), []
            logger.warning(f"Trade has unexpected structure: {len(rows)} entries, skipping")
            return [], []

        if crypto_entry is None:
            logger.warning(f"Trade missing crypto entry: {len(rows)} entries, skipping")
            return [], []

        # Extract data from both entries
        refid = crypto_entry.get("refid", "")
        crypto_asset = self._normalize_asset(crypto_entry.get("asset", ""))
        crypto_amount = Decimal(crypto_entry.get("amount", "0"))
        crypto_fee = Decimal(crypto_entry.get("fee", "0") or "0")
        fiat_amount = Decimal(fiat_entry.get("amount", "0"))
        fiat_fee = Decimal(fiat_entry.get("fee", "0") or "0")
        fiat_currency = self._normalize_asset(fiat_entry.get("asset", ""))

        # Determine transaction type based on crypto amount sign
        # Positive crypto = Buy, Negative crypto = Sell
        if crypto_amount > 0:
            transaction_type = "Buy"
            quantity = crypto_amount - crypto_fee  # Net crypto received after fee
            cost = abs(fiat_amount)  # fiat_amount is negative (spent)
        else:
            transaction_type = "Sell"
            quantity = abs(crypto_amount) + crypto_fee  # Total crypto leaving account
            cost = fiat_amount  # fiat_amount is positive (received)

        price_per_unit = cost / quantity if quantity != 0 else None
        total_fees = fiat_fee + crypto_fee

        transaction = ParsedTransaction(
            trade_date=trade_date,
            symbol=crypto_asset,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_unit=price_per_unit,
            amount=cost,
            fees=total_fees,
            currency="USD",
            notes=f"Kraken trade - {refid}",
            raw_data={"crypto": dict(crypto_entry), "fiat": dict(fiat_entry)},
        )

        # Trade Settlement for cash impact (dual-entry accounting)
        # Total cash impact = fiat_amount - fiat_fee (fee reduces cash further)
        settlement = ParsedCashTransaction(
            date=trade_date,
            transaction_type="Trade Settlement",
            amount=fiat_amount - fiat_fee,
            currency=fiat_currency,
            notes=f"Settlement for {crypto_asset} {transaction_type} - {refid}",
            raw_data=dict(fiat_entry),
        )

        return [transaction], [settlement]

    def _parse_crypto_to_crypto_trade(
        self, entries: list[dict], trade_date: date
    ) -> list[ParsedTransaction]:
        """Parse a crypto-to-crypto trade (no fiat involved).

        For buys: net quantity = amount - fee (fee reduces what you receive)
        For sells: quantity = abs(amount) + fee (fee adds to what you give up)
        """
        refid = entries[0].get("refid", "")
        transactions = []

        for entry in entries:
            asset = self._normalize_asset(entry.get("asset", ""))
            amount = Decimal(entry.get("amount", "0"))
            fee = Decimal(entry.get("fee", "0") or "0")

            if amount > 0:
                transaction_type = "Buy"
                quantity = amount - fee
            else:
                transaction_type = "Sell"
                quantity = abs(amount) + fee

            transactions.append(
                ParsedTransaction(
                    trade_date=trade_date,
                    symbol=asset,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    price_per_unit=None,
                    amount=None,
                    fees=fee,
                    currency="USD",
                    notes=f"Kraken crypto-to-crypto trade ({transaction_type.lower()}) - {refid}",
                    raw_data=dict(entry),
                )
            )

        return transactions
