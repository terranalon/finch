"""Reusable response formatting helpers.

Pure functions for converting service-layer dataclasses to response dicts.
"""

from decimal import Decimal

from app.services.portfolio.types import AccountHolding, PositionResult
from app.services.shared.currency_service import CurrencyService


def to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def convert_price(
    currency_svc: CurrencyService,
    price: float | None,
    asset_currency: str,
    display_currency: str,
) -> float | None:
    if price is None:
        return None
    if display_currency == asset_currency:
        return price
    rate = currency_svc.get_exchange_rate(asset_currency, display_currency)
    if rate is None:
        return price
    return float(Decimal(str(price)) * rate)


def format_account_holding(a: AccountHolding) -> dict:
    return {
        "holding_id": a.holding_id,
        "account_id": a.account_id,
        "account_name": a.account_name,
        "account_type": a.account_type,
        "institution": a.institution,
        "quantity": float(a.quantity),
        "cost_basis_native": float(a.cost_basis_native),
        "market_value_native": to_float(a.market_value_native),
        "pnl_native": to_float(a.pnl_native),
        "cost_basis": float(a.cost_basis_usd),
        "market_value": to_float(a.market_value_usd),
        "pnl": to_float(a.pnl_usd),
        "pnl_pct": to_float(a.pnl_pct),
        "strategy_horizon": a.strategy_horizon,
    }


_MOVER_KEYS = frozenset(
    {
        "asset_id",
        "symbol",
        "name",
        "asset_class",
        "current_price",
        "day_change",
        "day_change_pct",
        "currency",
    }
)


def format_mover(p: PositionResult) -> dict:
    """Format a PositionResult as a mover dict (subset of position fields)."""
    return {k: v for k, v in format_position(p).items() if k in _MOVER_KEYS}


def format_position(p: PositionResult) -> dict:
    return {
        "asset_id": p.asset_id,
        "symbol": p.symbol,
        "name": p.name,
        "asset_class": p.asset_class,
        "category": p.category,
        "industry": p.industry,
        "currency": p.currency,
        "is_favorite": p.is_favorite,
        "current_price": to_float(p.current_price),
        "previous_close_price": to_float(p.previous_close_price),
        "day_change": to_float(p.day_change),
        "day_change_pct": to_float(p.day_change_pct),
        "day_change_date": p.day_change_date,
        "is_market_closed": p.is_market_closed,
        "market_cap": to_float(p.market_cap),
        "week_change_pct": to_float(p.week_change_pct),
        "total_quantity": to_float(p.total_quantity),
        "total_cost_basis_native": to_float(p.total_cost_basis_native),
        "total_market_value_native": to_float(p.total_market_value_native),
        "total_pnl_native": to_float(p.total_pnl_native),
        "avg_cost_per_unit_native": to_float(p.avg_cost_per_unit_native),
        "total_cost_basis": to_float(p.total_cost_basis_usd),
        "total_market_value": to_float(p.total_market_value_usd),
        "total_pnl": to_float(p.total_pnl_usd),
        "total_pnl_pct": to_float(p.total_pnl_pct),
        "account_count": p.account_count,
        "avg_cost_per_unit": to_float(p.avg_cost_per_unit_usd),
        "accounts": [format_account_holding(a) for a in p.accounts],
    }
