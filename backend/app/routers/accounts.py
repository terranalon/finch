"""Accounts API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.account import Account as AccountSchema
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=PaginatedResponse[AccountSchema])
async def list_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    is_active: bool = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get paginated list of accounts for the current user.

    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return (1-100)
        - is_active: Filter by active status
        - portfolio_id: Filter by specific portfolio (must belong to user)

    Returns:
        Paginated response with items, total count, and has_more flag
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit, has_more=False)

    query = db.query(Account).filter(Account.id.in_(allowed_account_ids))

    if is_active is not None:
        query = query.filter(Account.is_active == is_active)

    # Get total count before pagination
    total = query.count()

    # Get paginated items
    accounts = query.offset(skip).limit(limit).all()

    return PaginatedResponse(
        items=accounts,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(accounts)) < total,
    )


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
    """Create a new account linked to specified portfolios."""
    # Validate all portfolio_ids belong to user
    user_portfolio_ids = {p.id for p in current_user.portfolios}
    invalid_ids = set(account.portfolio_ids) - user_portfolio_ids
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Portfolio {next(iter(invalid_ids))} not found or doesn't belong to you",
        )

    # Create account
    account_data = account.model_dump(exclude={"portfolio_ids"})
    db_account = Account(**account_data)

    # Link to portfolios
    portfolios = db.query(Portfolio).filter(Portfolio.id.in_(account.portfolio_ids)).all()
    db_account.portfolios = portfolios

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
