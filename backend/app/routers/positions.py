"""Positions API router - aggregated holdings by asset."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.services.portfolio.position_service import PositionService
from app.services.portfolio.types import AccountHolding, PositionResult
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper
from app.services.shared.currency_service import CurrencyService

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("")
async def list_positions(
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Get positions aggregated by asset across all user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    positions = PositionService(db).get_positions(allowed_account_ids)
    result = [_format_position(p) for p in positions]

    # Convert USD values to display currency
    if display_currency != "USD":
        result = [
            CurrencyConversionHelper.convert_position_dict(db, pos, display_currency)
            for pos in result
        ]
    else:
        for pos in result:
            pos["display_currency"] = "USD"

    # Add display-currency price fields
    currency_svc = CurrencyService(db)
    for pos in result:
        pos["current_value"] = pos["total_market_value"]
        pos["current_price_display"] = _convert_price(
            currency_svc, pos["current_price"], pos["currency"], display_currency
        )

    return result


# ------------------------------------------------------------------
# Response formatting
# ------------------------------------------------------------------


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _convert_price(
    currency_svc: CurrencyService,
    price: float | None,
    asset_currency: str,
    display_currency: str,
) -> float | None:
    """Convert a price from asset currency to display currency."""
    if price is None:
        return None
    if display_currency == asset_currency:
        return price
    rate = currency_svc.get_exchange_rate(asset_currency, display_currency)
    if rate is None:
        return price
    return float(Decimal(str(price)) * rate)


def _format_account(a: AccountHolding) -> dict:
    return {
        "holding_id": a.holding_id,
        "account_id": a.account_id,
        "account_name": a.account_name,
        "account_type": a.account_type,
        "institution": a.institution,
        "quantity": float(a.quantity),
        "cost_basis_native": float(a.cost_basis_native),
        "market_value_native": _to_float(a.market_value_native),
        "pnl_native": _to_float(a.pnl_native),
        "cost_basis": float(a.cost_basis_usd),
        "market_value": _to_float(a.market_value_usd),
        "pnl": _to_float(a.pnl_usd),
        "pnl_pct": _to_float(a.pnl_pct),
        "strategy_horizon": a.strategy_horizon,
    }


def _format_position(p: PositionResult) -> dict:
    return {
        "asset_id": p.asset_id,
        "symbol": p.symbol,
        "name": p.name,
        "asset_class": p.asset_class,
        "category": p.category,
        "industry": p.industry,
        "currency": p.currency,
        "is_favorite": p.is_favorite,
        "current_price": _to_float(p.current_price),
        "previous_close_price": _to_float(p.previous_close_price),
        "day_change": _to_float(p.day_change),
        "day_change_pct": _to_float(p.day_change_pct),
        "day_change_date": p.day_change_date,
        "is_market_closed": p.is_market_closed,
        "total_quantity": _to_float(p.total_quantity),
        "total_cost_basis_native": _to_float(p.total_cost_basis_native),
        "total_market_value_native": _to_float(p.total_market_value_native),
        "total_pnl_native": _to_float(p.total_pnl_native),
        "avg_cost_per_unit_native": _to_float(p.avg_cost_per_unit_native),
        "total_cost_basis": _to_float(p.total_cost_basis_usd),
        "total_market_value": _to_float(p.total_market_value_usd),
        "total_pnl": _to_float(p.total_pnl_usd),
        "total_pnl_pct": _to_float(p.total_pnl_pct),
        "account_count": p.account_count,
        "avg_cost_per_unit": _to_float(p.avg_cost_per_unit_usd),
        "accounts": [_format_account(a) for a in p.accounts],
    }
