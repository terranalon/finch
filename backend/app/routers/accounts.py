"""Accounts API router."""

from dataclasses import asdict
from datetime import date
from typing import Any

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
from app.schemas.holding import ReconstructionStatsResponse
from app.services.portfolio.holding_service import HoldingService
from app.services.portfolio.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.portfolio.snapshot_service import SnapshotService
from app.services.repositories import AccountRepository

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def raise_duplicate_account_name(account_name: str, portfolio_name: str) -> None:
    """Raise HTTP 409 when an account name already exists in a portfolio."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            f"An account named '{account_name}' already exists in portfolio "
            f"'{portfolio_name}'. Rename one of the accounts if you want both "
            f"in the same portfolio."
        ),
    )


def verify_account_ownership(account_id: int, current_user: User, db: Session) -> None:
    """Raise HTTP 404 if account_id does not belong to the current user."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )


@router.get("", response_model=PaginatedResponse[AccountSchema])
async def list_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    is_active: bool | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of accounts for the current user."""
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
    verify_account_ownership(account_id, current_user, db)

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

    # Fetch target portfolios (reused for both duplicate check and linking)
    portfolios = db.query(Portfolio).filter(Portfolio.id.in_(account.portfolio_ids)).all()

    # Check for duplicate account name in each target portfolio
    repo = AccountRepository(db)
    for portfolio in portfolios:
        if repo.find_by_name_in_portfolio(account.name, portfolio.id):
            raise_duplicate_account_name(account.name, portfolio.name)

    # Create account
    account_data = account.model_dump(exclude={"portfolio_ids"})
    db_account = Account(**account_data)
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
    verify_account_ownership(account_id, current_user, db)

    db_account = db.query(Account).filter(Account.id == account_id).first()

    update_data = account_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        repo = AccountRepository(db)
        for portfolio in db_account.portfolios:
            if repo.find_by_name_in_portfolio(
                update_data["name"], portfolio.id, exclude_account_id=account_id
            ):
                raise_duplicate_account_name(update_data["name"], portfolio.name)

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
    verify_account_ownership(account_id, current_user, db)

    db_account = db.query(Account).filter(Account.id == account_id).first()
    db.delete(db_account)
    db.commit()
    return None


@router.post("/{account_id}/reconstructed-holdings", response_model=ReconstructionStatsResponse)
async def reconstruct_holdings(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconstruct holdings for an account from transaction history (must belong to user)."""
    verify_account_ownership(account_id, current_user, db)

    svc = HoldingService(db)
    stats = svc.reconstruct_holdings(account_id)
    db.commit()
    return asdict(stats)


@router.get("/{account_id}/reconstruction-validation", response_model=dict[str, Any])
async def validate_reconstruction(
    account_id: int,
    as_of_date: date | None = Query(default=None, description="Date to validate (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate portfolio reconstruction accuracy (account must belong to user).

    Compares reconstructed holdings (from transaction replay) with actual holdings.
    """
    verify_account_ownership(account_id, current_user, db)

    return PortfolioReconstructionService.validate_reconstruction(db, account_id, as_of_date)


@router.post("/{account_id}/snapshot-backfill", response_model=dict[str, Any])
async def backfill_historical_snapshots(
    account_id: int,
    start_date: date = Query(..., description="Start date for backfill"),
    end_date: date | None = Query(default=None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backfill historical snapshots (account must belong to user).

    Generates portfolio snapshots for every day between start_date and end_date
    by reconstructing holdings from transaction history.
    """
    verify_account_ownership(account_id, current_user, db)

    if not end_date:
        end_date = date.today()

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date"
        )

    total_days = (end_date - start_date).days + 1

    if total_days > 730:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range too large ({total_days} days). Maximum is 730 days (2 years).",
        )

    try:
        stats = SnapshotService(db).backfill_historical_snapshots(account_id, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {"status": "completed", "message": "Backfill completed successfully", **stats}
