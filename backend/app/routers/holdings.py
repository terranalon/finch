"""Holdings API router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account, Asset, Holding
from app.models.user import User
from app.schemas import Holding as HoldingSchema
from app.schemas import HoldingCreate, HoldingUpdate

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.get("")
async def list_holdings(
    skip: int = 0,
    limit: int = 100,
    account_id: int = None,
    asset_id: int = None,
    is_active: bool = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Get list of holdings with optional filters (filtered by user's accounts).

    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return
        - account_id: Filter by account ID
        - asset_id: Filter by asset ID
        - is_active: Filter by active status
        - portfolio_id: Filter by specific portfolio (must belong to user)

    Returns holdings with account and asset details.
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    query = (
        db.query(Holding, Account, Asset)
        .join(Account, Holding.account_id == Account.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(Holding.account_id.in_(allowed_account_ids))
    )

    # Apply filters
    if account_id is not None:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=404, detail="Account not found")
        query = query.filter(Holding.account_id == account_id)
    if asset_id is not None:
        query = query.filter(Holding.asset_id == asset_id)
    if is_active is not None:
        query = query.filter(Holding.is_active == is_active)

    results = query.offset(skip).limit(limit).all()

    holdings_data = []
    for holding, account, asset in results:
        holdings_data.append(
            {
                "id": holding.id,
                "account_id": holding.account_id,
                "asset_id": holding.asset_id,
                "quantity": float(holding.quantity),
                "cost_basis": float(holding.cost_basis),
                "strategy_horizon": holding.strategy_horizon,
                "tags": holding.tags,
                "is_active": holding.is_active,
                "closed_at": holding.closed_at.isoformat() if holding.closed_at else None,
                "created_at": holding.created_at.isoformat(),
                "updated_at": holding.updated_at.isoformat(),
                "account": {
                    "id": account.id,
                    "name": account.name,
                    "type": account.account_type,
                    "institution": account.institution,
                    "currency": account.currency,
                },
                "asset": {
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_class": asset.asset_class,
                    "category": asset.category,
                },
            }
        )

    return holdings_data


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

    # Verify holding belongs to user's account
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
    """
    Create a new holding (account must belong to user).

    Validates that:
    - Account exists, is active, and belongs to user
    - Asset exists
    - No duplicate holding exists for the same account/asset combination
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding_data.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {holding_data.account_id} not found",
        )

    # Validate account exists and is active
    account = db.query(Account).filter(Account.id == holding_data.account_id).first()
    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Account {account.name} is not active"
        )

    # Validate asset exists
    asset = db.query(Asset).filter(Asset.id == holding_data.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {holding_data.asset_id} not found",
        )

    # Check for duplicate holding
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

    # Create new holding
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

    # Verify holding belongs to user's account
    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    # Update only provided fields
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
    """
    Delete a holding (must belong to user's accounts).

    Note: This will cascade delete associated holding_lots and transactions.
    """
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    # Verify holding belongs to user's account
    allowed_account_ids = get_user_account_ids(current_user, db)
    if holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Holding with id {holding_id} not found"
        )

    db.delete(holding)
    db.commit()

    return None


@router.post("/reconstruct/{account_id}")
async def reconstruct_holdings(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Reconstruct holdings for an account from transaction history (must belong to user).

    This replays all transactions to recalculate quantities and cost basis,
    then updates the Holding records.
    """
    from datetime import date
    from decimal import Decimal

    from app.services.portfolio_reconstruction_service import PortfolioReconstructionService

    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    stats = {
        "account_id": account_id,
        "holdings_updated": 0,
        "holdings_activated": 0,
        "holdings_deactivated": 0,
    }

    # Reconstruct holdings as of today
    today = date.today()
    reconstructed = PortfolioReconstructionService.reconstruct_holdings(
        db, account_id, today, apply_ticker_changes=False
    )

    # Build map of reconstructed holdings by asset_id
    reconstructed_map = {h["asset_id"]: h for h in reconstructed}

    # Get all holdings for this account
    holdings = db.query(Holding).filter(Holding.account_id == account_id).all()

    # Update existing holdings
    for holding in holdings:
        recon = reconstructed_map.get(holding.asset_id)

        if recon:
            old_qty = holding.quantity
            holding.quantity = recon["quantity"]
            holding.cost_basis = recon["cost_basis"]
            holding.is_active = recon["quantity"] != Decimal("0")

            if old_qty == Decimal("0") and holding.quantity != Decimal("0"):
                stats["holdings_activated"] += 1
            elif old_qty != Decimal("0") and holding.quantity == Decimal("0"):
                stats["holdings_deactivated"] += 1

            stats["holdings_updated"] += 1
            del reconstructed_map[holding.asset_id]
        else:
            if holding.quantity == Decimal("0"):
                holding.is_active = False

    db.commit()

    stats["reconstructed_count"] = len(reconstructed)
    return stats
