"""Accounts API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account
from app.models.user import User
from app.schemas.account import Account as AccountSchema
from app.schemas.account import AccountCreate, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountSchema])
async def list_accounts(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of accounts for the current user.

    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return
        - is_active: Filter by active status
        - portfolio_id: Filter by specific portfolio (must belong to user)
    """
    # Get user's portfolio IDs
    portfolio_ids = [p.id for p in current_user.portfolios]
    if not portfolio_ids:
        return []

    # If portfolio_id specified, validate it belongs to user
    if portfolio_id:
        if portfolio_id not in portfolio_ids:
            return []  # Portfolio doesn't belong to user
        portfolio_ids = [portfolio_id]

    query = db.query(Account).filter(Account.portfolio_id.in_(portfolio_ids))

    if is_active is not None:
        query = query.filter(Account.is_active == is_active)

    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific account by ID (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    account = db.query(Account).filter(Account.id == account_id).first()
    return account


@router.post("", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new account (must specify user's portfolio_id)."""
    # Verify portfolio belongs to user
    portfolio_ids = [p.id for p in current_user.portfolios]
    if account.portfolio_id not in portfolio_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create account in a portfolio you don't own",
        )

    db_account = Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.put("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing account (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    db_account = db.query(Account).filter(Account.id == account_id).first()

    update_data = account_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_account, field, value)

    db.commit()
    db.refresh(db_account)
    return db_account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an account (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    db_account = db.query(Account).filter(Account.id == account_id).first()
    db.delete(db_account)
    db.commit()
    return None
