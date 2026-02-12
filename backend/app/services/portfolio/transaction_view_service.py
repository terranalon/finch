"""Transaction view business logic - trade computation, forex parsing, cash conversion."""

import re
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, Asset, Holding, Transaction
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.portfolio.transaction_view_types import (
    CashActivityItem,
    DividendItem,
    ForexItem,
    TradeItem,
)
from app.services.repositories.transaction_repository import TransactionRepository
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper

_CRYPTO_CASH_TYPES = ("Deposit", "Withdrawal", "Custody Fee")


class TransactionViewService:
    """Read-only service for enriched transaction views."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = TransactionRepository(db)

    def get_trades(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        display_currency: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TradeItem], int]:
        if not account_ids:
            return [], 0

        total = self._repo.count_trades(account_ids, account_id=account_id, symbol=symbol)
        rows = self._repo.find_trades(
            account_ids,
            account_id=account_id,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )

        trades: list[TradeItem] = []
        for txn, _, asset, account in rows:
            qty = txn.quantity or Decimal("0")
            price = txn.price_per_unit or Decimal("0")
            fees = txn.fees or Decimal("0")
            trade_total = (qty * price) + fees

            native_currency = _resolve_native_currency(asset, txn.notes)

            if display_currency and display_currency != native_currency:
                convert = CurrencyConversionHelper.convert_value
                price = convert(self._db, price, native_currency, display_currency, txn.date)
                fees = convert(self._db, fees, native_currency, display_currency, txn.date)
                trade_total = convert(
                    self._db, trade_total, native_currency, display_currency, txn.date
                )
                output_currency = display_currency
            else:
                output_currency = native_currency

            trades.append(
                TradeItem(
                    id=txn.id,
                    date=txn.date,
                    symbol=asset.symbol,
                    asset_name=asset.name,
                    asset_class=asset.asset_class,
                    action=txn.type,
                    quantity=qty,
                    price_per_unit=price,
                    fees=fees,
                    total=trade_total,
                    currency=output_currency,
                    account_name=account.name,
                    notes=txn.notes,
                ),
            )

        return trades, total

    def get_dividends(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DividendItem], int]:
        if not account_ids:
            return [], 0

        total = self._repo.count_dividends(account_ids, account_id=account_id, symbol=symbol)
        rows = self._repo.find_dividends(
            account_ids,
            account_id=account_id,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )

        items = [
            DividendItem(
                id=txn.id,
                date=txn.date,
                symbol=asset.symbol,
                asset_name=asset.name,
                type=txn.type,
                amount=txn.amount or Decimal("0"),
                currency=asset.currency,
                account_name=account.name,
                notes=txn.notes,
            )
            for txn, _, asset, account in rows
        ]
        return items, total

    def get_forex(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ForexItem], int]:
        if not account_ids:
            return [], 0

        # Load all rows to get accurate count after deduplication
        all_rows = self._repo.find_forex(
            account_ids,
            account_id=account_id,
            limit=10000,
            offset=0,
        )

        all_forex: list[ForexItem] = []
        seen_legacy_pairs: set[tuple[str, ...]] = set()

        for txn, _, asset, account in all_rows:
            if txn.to_holding_id is not None:
                all_forex.append(self._build_new_format_forex(txn, asset, account))
            else:
                parsed = self.parse_legacy_forex_notes(txn.notes)
                if not parsed:
                    continue
                from_amt, from_curr, to_amt, to_curr, rate = parsed
                pair_key = (str(txn.date), from_curr, to_curr, str(from_amt), str(to_amt))
                if pair_key in seen_legacy_pairs:
                    continue
                seen_legacy_pairs.add(pair_key)

                all_forex.append(
                    ForexItem(
                        id=txn.id,
                        date=txn.date,
                        from_currency=from_curr,
                        from_amount=from_amt,
                        to_currency=to_curr,
                        to_amount=to_amt,
                        exchange_rate=rate,
                        account_name=account.name,
                        notes=txn.notes,
                    ),
                )

        total = len(all_forex)
        return all_forex[offset : offset + limit], total

    def _build_new_format_forex(
        self, txn: Transaction, asset: Asset, account: Account
    ) -> ForexItem:
        to_holding = self._db.query(Holding).filter(Holding.id == txn.to_holding_id).first()
        to_asset = (
            self._db.query(Asset).filter(Asset.id == to_holding.asset_id).first()
            if to_holding
            else None
        )
        return ForexItem(
            id=txn.id,
            date=txn.date,
            from_currency=asset.symbol,
            from_amount=txn.amount or Decimal("0"),
            to_currency=to_asset.symbol if to_asset else "???",
            to_amount=txn.to_amount or Decimal("0"),
            exchange_rate=txn.exchange_rate or Decimal("0"),
            account_name=account.name,
            notes=txn.notes,
        )

    def get_cash_activity(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        display_currency: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CashActivityItem], int]:
        if not account_ids:
            return [], 0

        total = self._repo.count_cash_activity(account_ids, account_id=account_id)
        rows = self._repo.find_cash_activity(
            account_ids, account_id=account_id, limit=limit, offset=offset
        )

        items: list[CashActivityItem] = []
        for txn, _, asset, account in rows:
            amount, fees, native_currency = self._compute_cash_values(txn, asset)

            if display_currency and display_currency != native_currency:
                convert = CurrencyConversionHelper.convert_value
                amount = convert(self._db, amount, native_currency, display_currency, txn.date)
                if fees is not None:
                    fees = convert(self._db, fees, native_currency, display_currency, txn.date)
                output_currency = display_currency
            else:
                output_currency = native_currency

            items.append(
                CashActivityItem(
                    id=txn.id,
                    date=txn.date,
                    type=txn.type,
                    symbol=asset.symbol if asset.asset_class != "Cash" else None,
                    amount=amount,
                    fees=fees,
                    currency=output_currency,
                    account_name=account.name,
                    notes=txn.notes,
                ),
            )

        return items, total

    def _compute_cash_values(
        self, txn: Transaction, asset: Asset
    ) -> tuple[Decimal, Decimal | None, str]:
        """Compute amount, fees, and native currency for a cash activity row.

        For crypto assets with cash-like transaction types, converts quantity
        to USD value using the asset price. Otherwise uses the raw amount.
        """
        if asset.asset_class == "Crypto" and txn.type in _CRYPTO_CASH_TYPES:
            return self._compute_crypto_cash_values(txn, asset)

        amount = txn.amount or Decimal("0")
        fees = txn.fees if txn.fees and txn.fees > 0 else None
        native_currency = asset.currency or asset.symbol
        return amount, fees, native_currency

    def _compute_crypto_cash_values(
        self, txn: Transaction, asset: Asset
    ) -> tuple[Decimal, Decimal | None, str]:
        """Compute cash values for crypto deposit/withdrawal/custody fee."""
        quantity = txn.quantity or Decimal("0")
        price = txn.price_per_unit

        if price is None or price == 0:
            price = PriceFetcher.get_price_for_date(self._db, asset.id, txn.date)

        if price is not None and price != 0:
            amount = abs(quantity) * price
            if quantity < 0:
                amount = -amount
            fees = txn.fees * price if txn.fees and txn.fees > 0 else None
            return amount, fees, "USD"

        fees = txn.fees if txn.fees and txn.fees > 0 else None
        return quantity, fees, asset.symbol

    @staticmethod
    def parse_legacy_forex_notes(
        notes: str | None,
    ) -> tuple[Decimal, str, Decimal, str, Decimal] | None:
        if not notes:
            return None
        match = re.search(r"Convert ([\d.]+) (\w+) to ([\d.]+) (\w+) @ ([\d.]+)", notes)
        if not match:
            return None
        return (
            Decimal(match.group(1)),
            match.group(2),
            Decimal(match.group(3)),
            match.group(4),
            Decimal(match.group(5)),
        )


def _resolve_native_currency(asset: Asset, notes: str | None) -> str:
    native_currency = asset.currency or "USD"
    if notes and "Bit2C" in notes:
        native_currency = "ILS"
    return native_currency
