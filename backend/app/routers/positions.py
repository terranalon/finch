"""Positions API router - aggregated holdings by asset."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.services.portfolio.position_service import PositionService
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper
from app.services.shared.currency_service import CurrencyService
from app.services.shared.response_formatters import convert_price, format_position

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
    result = [format_position(p) for p in positions]

    if display_currency != "USD":
        result = [
            CurrencyConversionHelper.convert_position_dict(db, pos, display_currency)
            for pos in result
        ]
    else:
        for pos in result:
            pos["display_currency"] = "USD"

    currency_svc = CurrencyService(db)
    for pos in result:
        pos["current_value"] = pos["total_market_value"]
        pos["current_price_display"] = convert_price(
            currency_svc, pos["current_price"], pos["currency"], display_currency
        )

    return result
