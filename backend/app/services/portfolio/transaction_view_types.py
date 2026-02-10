"""Value objects for transaction view services."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class TradeItem:
    id: int
    date: date
    symbol: str
    asset_name: str
    asset_class: str
    action: str
    quantity: Decimal
    price_per_unit: Decimal
    fees: Decimal
    total: Decimal
    currency: str
    account_name: str
    notes: str | None


@dataclass
class DividendItem:
    id: int
    date: date
    symbol: str
    asset_name: str
    type: str
    amount: Decimal
    currency: str
    account_name: str
    notes: str | None


@dataclass
class ForexItem:
    id: int
    date: date
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    exchange_rate: Decimal
    account_name: str
    notes: str | None


@dataclass
class CashActivityItem:
    id: int
    date: date
    type: str
    symbol: str | None
    amount: Decimal
    fees: Decimal | None
    currency: str
    account_name: str
    notes: str | None
