"""Portfolios API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import (
    get_user_account,
    get_user_account_ids,
    validate_user_portfolio,
)
from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.portfolio_account import portfolio_accounts
from app.models.user import User
from app.routers.accounts import raise_duplicate_account_name
from app.schemas.account import Account as AccountSchema
from app.schemas.portfolio import (
    DeletionPreview,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioWithAccountCount,
)
from app.schemas.portfolio import (
    Portfolio as PortfolioSchema,
)
from app.services.portfolio.portfolio_management_service import PortfolioManagementService
from app.services.repositories import AccountRepository

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioWithAccountCount])
async def list_portfolios(
    include_values: bool = Query(False, description="Include total portfolio values"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of portfolios for the current user with account counts and optional values.
    """
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()

    return [
        _to_portfolio_with_account_count(portfolio, db, include_values) for portfolio in portfolios
    ]


def _to_portfolio_with_account_count(
    portfolio: Portfolio,
    db: Session,
    include_values: bool = False,
) -> PortfolioWithAccountCount:
    """Convert a Portfolio model to PortfolioWithAccountCount schema."""
    total_value = (
        PortfolioManagementService(db).calculate_portfolio_value(portfolio)
        if include_values
        else None
    )
    base = PortfolioSchema.model_validate(portfolio)
    return PortfolioWithAccountCount(
        **base.model_dump(),
        account_count=len(portfolio.accounts),
        total_value=total_value,
    )


@router.post("", response_model=PortfolioSchema, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new portfolio for the current user."""
    db_portfolio = Portfolio(
        user_id=current_user.id,
        name=portfolio.name,
        description=portfolio.description,
        default_currency=portfolio.default_currency,
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


@router.get("/{portfolio_id}", response_model=PortfolioWithAccountCount)
async def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific portfolio by ID (must belong to user)."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with id {portfolio_id} not found",
        )

    return _to_portfolio_with_account_count(portfolio, db)


@router.put("/{portfolio_id}", response_model=PortfolioSchema)
async def update_portfolio(
    portfolio_id: str,
    portfolio_update: PortfolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing portfolio (must belong to user)."""
    db_portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with id {portfolio_id} not found",
        )

    update_data = portfolio_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_portfolio, field, value)

    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


@router.get("/{portfolio_id}/deletion-preview", response_model=DeletionPreview)
async def get_deletion_preview(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview what happens when this portfolio is deleted."""
    portfolio = validate_user_portfolio(current_user, db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    svc = PortfolioManagementService(db)
    exclusive, shared = svc.categorize_accounts_for_deletion(portfolio)

    warning = (
        f"This will permanently delete {len(exclusive)} account(s) and all their data."
        if exclusive
        else ""
    )

    return DeletionPreview(
        portfolio_name=portfolio.name,
        exclusive_accounts=exclusive,  # ty: ignore[invalid-argument-type] — Pydantic coerces ORM objects via from_attributes
        shared_accounts=shared,
        warning=warning,
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    confirm: bool = Query(False, description="Must be true to delete portfolio with accounts"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a portfolio. Exclusive accounts are deleted, shared accounts are unlinked."""
    portfolio = validate_user_portfolio(current_user, db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    portfolio_count = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).count()
    if portfolio_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your only portfolio"
        )

    if portfolio.accounts and not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio has accounts. Use ?confirm=true or call deletion-preview first.",
        )

    svc = PortfolioManagementService(db)
    svc.delete_portfolio_cascade(portfolio)
    db.commit()


@router.put("/{portfolio_id}/set-default", response_model=PortfolioSchema)
async def set_default_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set a portfolio as the default for the current user.
    This will unset any other portfolio that was previously marked as default.
    """
    db_portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .first()
    )
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with id {portfolio_id} not found",
        )

    db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.is_default == True,  # noqa: E712
    ).update({"is_default": False})

    db_portfolio.is_default = True
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


@router.post("/{portfolio_id}/accounts/{account_id}/link")
async def link_account_to_portfolio(
    portfolio_id: str,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Link an existing account to a portfolio."""
    portfolio = validate_user_portfolio(current_user, db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    account = get_user_account(current_user, db, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    existing = db.execute(
        portfolio_accounts.select().where(
            portfolio_accounts.c.portfolio_id == portfolio_id,
            portfolio_accounts.c.account_id == account_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already linked to this portfolio",
        )

    repo = AccountRepository(db)
    if repo.find_by_name_in_portfolio(account.name, portfolio_id):
        raise_duplicate_account_name(account.name, portfolio.name)

    db.execute(portfolio_accounts.insert().values(portfolio_id=portfolio_id, account_id=account_id))
    db.commit()

    return {"message": "Account linked successfully"}


@router.delete("/{portfolio_id}/accounts/{account_id}/unlink")
async def unlink_account_from_portfolio(
    portfolio_id: str,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Unlink an account from a portfolio. Blocked if it's the only portfolio."""
    portfolio = validate_user_portfolio(current_user, db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    account = get_user_account(current_user, db, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if len(account.portfolios) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink account from its only portfolio. Delete the account instead.",
        )

    db.execute(
        portfolio_accounts.delete().where(
            portfolio_accounts.c.portfolio_id == portfolio_id,
            portfolio_accounts.c.account_id == account_id,
        )
    )
    db.commit()

    return {"message": "Account unlinked successfully"}


@router.get("/{portfolio_id}/linkable-accounts", response_model=list[AccountSchema])
async def get_linkable_accounts(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get accounts that can be linked to this portfolio (not already linked)."""
    portfolio = validate_user_portfolio(current_user, db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    all_account_ids = get_user_account_ids(current_user, db)
    current_account_ids = {a.id for a in portfolio.accounts}
    linkable_ids = set(all_account_ids) - current_account_ids

    if not linkable_ids:
        return []

    return db.query(Account).filter(Account.id.in_(linkable_ids)).all()
