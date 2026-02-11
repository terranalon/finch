"""Transaction view business logic - trade computation, forex parsing, cash conversion."""

import logging
import re
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Holding
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.portfolio.transaction_view_types import (
    CashActivityItem,
    DividendItem,
    ForexItem,
    TradeItem,
)
from app.services.repositories.transaction_repository import TransactionRepository
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper

logger = logging.getLogger(__name__)


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
    ) -> list[TradeItem]:
        if not account_ids:
            return []

        rows = self._repo.find_trades(
            account_ids,
            account_id=account_id,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )

        trades: list[TradeItem] = []
        for txn, holding, asset, account in rows:
            qty = txn.quantity or Decimal("0")
            price = txn.price_per_unit or Decimal("0")
            fees = txn.fees or Decimal("0")
            total = (qty * price) + fees

            native_currency = _resolve_native_currency(asset, txn.notes)

            if display_currency and display_currency != native_currency:
                price = CurrencyConversionHelper.convert_value(
                    self._db, price, native_currency, display_currency, txn.date
                )
                fees = CurrencyConversionHelper.convert_value(
                    self._db, fees, native_currency, display_currency, txn.date
                )
                total = CurrencyConversionHelper.convert_value(
                    self._db, total, native_currency, display_currency, txn.date
                )
                output_currency = display_currency
            else:
                output_currency = native_currency

            trades = [
                *trades,
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
                    total=total,
                    currency=output_currency,
                    account_name=account.name,
                    notes=txn.notes,
                ),
            ]

        return trades

    def get_dividends(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DividendItem]:
        if not account_ids:
            return []

        rows = self._repo.find_dividends(
            account_ids,
            account_id=account_id,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )

        return [
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
            for txn, holding, asset, account in rows
        ]

    def get_forex(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ForexItem]:
        if not account_ids:
            return []

        rows = self._repo.find_forex(
            account_ids, account_id=account_id, limit=limit, offset=offset
        )

        forex_list: list[ForexItem] = []
        seen_legacy_pairs: set[tuple] = set()

        for txn, holding, asset, account in rows:
            if txn.to_holding_id is not None:
                to_holding = (
                    self._db.query(Holding)
                    .filter(Holding.id == txn.to_holding_id)
                    .first()
                )
                to_asset = (
                    self._db.query(Asset)
                    .filter(Asset.id == to_holding.asset_id)
                    .first()
                    if to_holding
                    else None
                )
                forex_list = [
                    *forex_list,
                    ForexItem(
                        id=txn.id,
                        date=txn.date,
                        from_currency=asset.symbol,
                        from_amount=txn.amount or Decimal("0"),
                        to_currency=to_asset.symbol if to_asset else "???",
                        to_amount=txn.to_amount or Decimal("0"),
                        exchange_rate=txn.exchange_rate or Decimal("0"),
                        account_name=account.name,
                        notes=txn.notes,
                    ),
                ]
            else:
                parsed = self.parse_legacy_forex_notes(txn.notes)
                if parsed:
                    from_amt, from_curr, to_amt, to_curr, rate = parsed
                    pair_key = (txn.date, from_curr, to_curr, str(from_amt), str(to_amt))
                    if pair_key in seen_legacy_pairs:
                        continue
                    seen_legacy_pairs.add(pair_key)

                    forex_list = [
                        *forex_list,
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
                    ]

        return forex_list

    def get_cash_activity(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        display_currency: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CashActivityItem]:
        if not account_ids:
            return []

        rows = self._repo.find_cash_activity(
            account_ids, account_id=account_id, limit=limit, offset=offset
        )

        items: list[CashActivityItem] = []
        for txn, holding, asset, account in rows:
            crypto_types = ("Deposit", "Withdrawal", "Custody Fee")
            fees = None

            if asset.asset_class == "Crypto" and txn.type in crypto_types:
                quantity = txn.quantity or Decimal("0")
                price = txn.price_per_unit

                if price is None or price == 0:
                    price = PriceFetcher.get_price_for_date(self._db, asset.id, txn.date)

                if price is not None and price != 0:
                    amount = abs(quantity) * price
                    if quantity < 0:
                        amount = -amount
                    if txn.fees and txn.fees > 0:
                        fees = txn.fees * price
                    native_currency = "USD"
                else:
                    amount = quantity
                    fees = txn.fees if txn.fees and txn.fees > 0 else None
                    native_currency = asset.symbol
            else:
                amount = txn.amount or Decimal("0")
                fees = txn.fees if txn.fees and txn.fees > 0 else None
                native_currency = asset.currency or asset.symbol

            needs_conversion = display_currency and display_currency != native_currency
            output_currency = display_currency if needs_conversion else native_currency

            if needs_conversion:
                amount = CurrencyConversionHelper.convert_value(
                    self._db, amount, native_currency, display_currency, txn.date
                )
                if fees is not None:
                    fees = CurrencyConversionHelper.convert_value(
                        self._db, fees, native_currency, display_currency, txn.date
                    )

            items = [
                *items,
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
            ]

        return items

    @staticmethod
    def parse_legacy_forex_notes(
        notes: str | None,
    ) -> tuple[Decimal, str, Decimal, str, Decimal] | None:
        if not notes:
            return None
        match = re.search(
            r"Convert ([\d.]+) (\w+) to ([\d.]+) (\w+) @ ([\d.]+)", notes
        )
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
