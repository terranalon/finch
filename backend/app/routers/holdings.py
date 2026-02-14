"""Holdings API router."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account, Asset, Holding
from app.models.user import User
from app.schemas import Holding as HoldingSchema
from app.schemas import HoldingCreate, HoldingUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.holding import HoldingDetailResponse
from app.services.portfolio.holding_service import HoldingService

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.get("", response_model=PaginatedResponse[HoldingDetailResponse])
async def list_holdings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    account_id: int | None = None,
    asset_id: int | None = None,
    is_active: bool | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of holdings with optional filters (filtered by user's accounts)."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse.create(items=[], total=0, skip=skip, limit=limit)

    if account_id is not None and account_id not in allowed_account_ids:
        raise HTTPException(status_code=404, detail="Account not found")

    svc = HoldingService(db)
    items, total = svc.list_holdings(
        allowed_account_ids,
        account_id=account_id,
        asset_id=asset_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )

    return PaginatedResponse.create(
        items=[asdict(h) for h in items], total=total, skip=skip, limit=limit
    )


@router.get("/{holding_id}", response_model=HoldingSchema)
async def get_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific holding by ID (must belong to user's accounts)."""
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    return holding


@router.post("", response_model=HoldingSchema, status_code=status.HTTP_201_CREATED)
async def create_holding(
    holding_data: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new holding (account must belong to user)."""
    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding_data.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {holding_data.account_id} not found",
        )

    account = db.query(Account).filter(Account.id == holding_data.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {holding_data.account_id} not found",
        )
    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Account {account.name} is not active"
        )

    asset = db.query(Asset).filter(Asset.id == holding_data.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {holding_data.asset_id} not found",
        )

    existing_holding = (
        db.query(Holding)
        .filter(
            Holding.account_id == holding_data.account_id, Holding.asset_id == holding_data.asset_id
        )
        .first()
    )
    if existing_holding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Holding already exists for {asset.symbol} in {account.name}",
        )

    new_holding = Holding(**holding_data.model_dump())
    db.add(new_holding)
    db.commit()
    db.refresh(new_holding)

    return new_holding


@router.put("/{holding_id}", response_model=HoldingSchema)
async def update_holding(
    holding_id: int,
    holding_data: HoldingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing holding (must belong to user's accounts)."""
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    update_data = holding_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(holding, field, value)

    db.commit()
    db.refresh(holding)

    return holding


@router.delete("/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a holding (must belong to user's accounts).

    Note: This will cascade delete associated holding_lots and transactions.
    """
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    db.delete(holding)
    db.commit()

    return None
