"""Transaction views API router - type-specific endpoints for the tabbed UI."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.schemas.transaction_views import (
    CashActivityResponse,
    DividendResponse,
    ForexResponse,
    TradeResponse,
)
from app.services.portfolio.transaction_view_service import TransactionViewService

router = APIRouter(prefix="/api/transactions", tags=["transaction-views"])


@router.get("/trades", response_model=list[TradeResponse])
async def list_trades(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TradeResponse]:
    """Get list of trade transactions (Buy/Sell) for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    trades = svc.get_trades(
        allowed_account_ids,
        account_id=account_id,
        symbol=symbol,
        display_currency=display_currency,
        limit=limit,
        offset=offset,
    )
    return [TradeResponse(**asdict(t)) for t in trades]


@router.get("/dividends", response_model=list[DividendResponse])
async def list_dividends(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DividendResponse]:
    """Get list of dividend and income transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    dividends = svc.get_dividends(
        allowed_account_ids,
        account_id=account_id,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )
    return [DividendResponse(**asdict(d)) for d in dividends]


@router.get("/forex", response_model=list[ForexResponse])
async def list_forex(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ForexResponse]:
    """Get list of forex conversion transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    forex = svc.get_forex(
        allowed_account_ids,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )
    return [ForexResponse(**asdict(f)) for f in forex]


@router.get("/cash", response_model=list[CashActivityResponse])
async def list_cash_activity(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CashActivityResponse]:
    """Get list of cash activity transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    cash = svc.get_cash_activity(
        allowed_account_ids,
        account_id=account_id,
        display_currency=display_currency,
        limit=limit,
        offset=offset,
    )
    return [CashActivityResponse(**asdict(c)) for c in cash]
