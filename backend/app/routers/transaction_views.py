"""Transaction views API router - type-specific endpoints for the tabbed UI."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.transaction_views import (
    CashActivityResponse,
    DividendResponse,
    ForexResponse,
    TradeResponse,
)
from app.services.portfolio.transaction_view_service import TransactionViewService

router = APIRouter(prefix="/api/transactions", tags=["transaction-views"])


@router.get("/trades", response_model=PaginatedResponse[TradeResponse])
async def list_trades(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get list of trade transactions (Buy/Sell) for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit, has_more=False)
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    trades, total = svc.get_trades(
        allowed_account_ids,
        account_id=account_id,
        symbol=symbol,
        display_currency=display_currency,
        limit=limit,
        offset=skip,
    )

    return PaginatedResponse(
        items=[TradeResponse(**asdict(t)) for t in trades],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(trades)) < total,
    )


@router.get("/dividends", response_model=PaginatedResponse[DividendResponse])
async def list_dividends(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get list of dividend and income transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit, has_more=False)
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    dividends, total = svc.get_dividends(
        allowed_account_ids,
        account_id=account_id,
        symbol=symbol,
        limit=limit,
        offset=skip,
    )

    return PaginatedResponse(
        items=[DividendResponse(**asdict(d)) for d in dividends],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(dividends)) < total,
    )


@router.get("/forex", response_model=PaginatedResponse[ForexResponse])
async def list_forex(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get list of forex conversion transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit, has_more=False)
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    forex, total = svc.get_forex(
        allowed_account_ids,
        account_id=account_id,
        limit=limit,
        offset=skip,
    )

    return PaginatedResponse(
        items=[ForexResponse(**asdict(f)) for f in forex],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(forex)) < total,
    )


@router.get("/cash", response_model=PaginatedResponse[CashActivityResponse])
async def list_cash_activity(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get list of cash activity transactions for user's accounts."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit, has_more=False)
    if account_id and account_id not in allowed_account_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    svc = TransactionViewService(db)
    cash, total = svc.get_cash_activity(
        allowed_account_ids,
        account_id=account_id,
        display_currency=display_currency,
        limit=limit,
        offset=skip,
    )

    return PaginatedResponse(
        items=[CashActivityResponse(**asdict(c)) for c in cash],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(cash)) < total,
    )
