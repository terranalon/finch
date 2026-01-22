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
            elif txn_type == "deposit":
                cash_txn = self._parse_deposit(row)
                if cash_txn:
                    cash_transactions.append(cash_txn)
            elif txn_type == "withdrawal":
                cash_txn = self._parse_withdrawal(row)
                if cash_txn:
                    cash_transactions.append(cash_txn)
            elif txn_type == "staking":
                dividend = self._parse_staking_reward(row)
                if dividend:
                    dividends.append(dividend)
            elif txn_type in ("transfer", "adjustment"):
                # Handle transfers/adjustments as cash transactions
                cash_txn = self._parse_transfer(row)
                if cash_txn:
                    cash_transactions.append(cash_txn)

        # Process grouped trades
        for refid, trade_rows in trades_by_refid.items():
            parsed_trades = self._parse_trade_group(trade_rows)
            transactions.extend(parsed_trades)

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

    def _parse_deposit(self, row: dict) -> ParsedCashTransaction | None:
        """Parse a deposit transaction."""
        dt = self._parse_datetime(row.get("time", ""))
        if not dt:
            return None

        amount = row.get("amount", "")
        if not amount:
            return None

        asset = self._normalize_asset(row.get("asset", ""))

        return ParsedCashTransaction(
            date=dt.date(),
            transaction_type="Deposit",
            amount=Decimal(amount),
            currency=asset,
            notes=f"Kraken deposit - {row.get('txid', '')}",
            raw_data=dict(row),
        )

    def _parse_withdrawal(self, row: dict) -> ParsedCashTransaction | None:
        """Parse a withdrawal transaction."""
        dt = self._parse_datetime(row.get("time", ""))
        if not dt:
            return None

        amount = row.get("amount", "")
        if not amount:
            return None

        asset = self._normalize_asset(row.get("asset", ""))
        fee = Decimal(row.get("fee", "0") or "0")

        return ParsedCashTransaction(
            date=dt.date(),
            transaction_type="Withdrawal",
            amount=Decimal(amount),  # Already negative in Kraken data
            currency=asset,
            notes=f"Kraken withdrawal - fee: {fee}",
            raw_data=dict(row),
        )

    def _parse_staking_reward(self, row: dict) -> ParsedTransaction | None:
        """Parse a staking reward as dividend-like income."""
        dt = self._parse_datetime(row.get("time", ""))
        if not dt:
            return None

        amount = row.get("amount", "")
        if not amount:
            return None

        asset = self._normalize_asset(row.get("asset", ""))

        return ParsedTransaction(
            trade_date=dt.date(),
            symbol=asset,
            transaction_type="Staking",
            amount=Decimal(amount),
            currency=asset,
            notes=f"Kraken staking reward - {row.get('txid', '')}",
            raw_data=dict(row),
        )

    def _parse_transfer(self, row: dict) -> ParsedCashTransaction | None:
        """Parse a transfer or adjustment transaction."""
        dt = self._parse_datetime(row.get("time", ""))
        if not dt:
            return None

        amount = row.get("amount", "")
        if not amount:
            return None

        asset = self._normalize_asset(row.get("asset", ""))
        txn_type = row.get("type", "transfer").capitalize()

        return ParsedCashTransaction(
            date=dt.date(),
            transaction_type=txn_type,
            amount=Decimal(amount),
            currency=asset,
            notes=f"Kraken {txn_type.lower()} - {row.get('txid', '')}",
            raw_data=dict(row),
        )

    def _parse_trade_group(self, rows: list[dict]) -> list[ParsedTransaction]:
        """Parse a group of trade rows with same refid.

        Kraken trades come in pairs: one negative (sold) and one positive (bought).
        Example: Buy BTC with USD creates:
        - ZUSD: -500.25 (sold USD)
        - XXBT: +0.01 (bought BTC)
        """
        if not rows:
            return []

        dt = self._parse_datetime(rows[0].get("time", ""))
        if not dt:
            return []

        # Separate into outgoing (negative) and incoming (positive) entries
        outgoing = [r for r in rows if Decimal(r.get("amount", "0")) < 0]
        incoming = [r for r in rows if Decimal(r.get("amount", "0")) > 0]

        transactions = []
        for in_row in incoming:
            in_asset = self._normalize_asset(in_row.get("asset", ""))
            in_amount = Decimal(in_row.get("amount", "0"))

            out_row = outgoing[0] if outgoing else None
            out_asset = self._normalize_asset(out_row.get("asset", "")) if out_row else ""
            out_amount = abs(Decimal(out_row.get("amount", "0"))) if out_row else Decimal("0")
            fee = Decimal(out_row.get("fee", "0") or "0") if out_row else Decimal("0")

            raw_data = {"buy": dict(in_row), "sell": dict(out_row) if out_row else {}}
            refid = in_row.get("refid", "")

            # If we received fiat, we sold crypto; otherwise we bought crypto
            if in_asset in FIAT_CURRENCIES:
                transactions.append(
                    ParsedTransaction(
                        trade_date=dt.date(),
                        symbol=out_asset,
                        transaction_type="Sell",
                        quantity=out_amount,
                        price_per_unit=in_amount / out_amount if out_amount > 0 else None,
                        amount=in_amount,
                        fees=fee,
                        currency=in_asset,
                        notes=f"Kraken trade - {refid}",
                        raw_data=raw_data,
                    )
                )
            else:
                transactions.append(
                    ParsedTransaction(
                        trade_date=dt.date(),
                        symbol=in_asset,
                        transaction_type="Buy",
                        quantity=in_amount,
                        price_per_unit=out_amount / in_amount if in_amount > 0 else None,
                        amount=out_amount,
                        fees=fee,
                        currency=out_asset if out_asset else in_asset,
                        notes=f"Kraken trade - {refid}",
                        raw_data=raw_data,
                    )
                )

        return transactions
