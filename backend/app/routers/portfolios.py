"""Portfolios API router."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.account import Account
from app.models.asset import Asset
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    Portfolio as PortfolioSchema,
)
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioWithAccountCount,
)
from app.services.currency_service import CurrencyService

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
    portfolios = (
        db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    )

    # Get account counts and optionally calculate values for each portfolio
    result = []
    for portfolio in portfolios:
        account_count = (
            db.query(Account).filter(Account.portfolio_id == portfolio.id).count()
        )

        total_value = None
        if include_values:
            total_value = _calculate_portfolio_value(db, portfolio)

        portfolio_dict = {
            "id": portfolio.id,
            "user_id": portfolio.user_id,
            "name": portfolio.name,
            "description": portfolio.description,
            "default_currency": portfolio.default_currency,
            "is_default": portfolio.is_default,
            "created_at": portfolio.created_at,
            "updated_at": portfolio.updated_at,
            "account_count": account_count,
            "total_value": total_value,
        }
        result.append(PortfolioWithAccountCount(**portfolio_dict))

    return result


def _calculate_portfolio_value(db: Session, portfolio: Portfolio) -> float:
    """Calculate total portfolio value in the portfolio's default currency."""
    total_value_usd = Decimal("0")

    # Get all accounts in this portfolio
    accounts = db.query(Account).filter(Account.portfolio_id == portfolio.id).all()

    for account in accounts:
        # Get active holdings for this account
        holdings = (
            db.query(Holding)
            .filter(Holding.account_id == account.id, Holding.is_active.is_(True))
            .all()
        )

        for holding in holdings:
            asset = db.query(Asset).filter(Asset.id == holding.asset_id).first()
            if not asset:
                continue

            asset_currency = asset.currency or "USD"

            # Handle Cash assets - value is the quantity itself
            if asset.asset_class == "Cash":
                if holding.quantity <= 0:
                    continue
                market_value_native = holding.quantity
            else:
                current_price = asset.last_fetched_price or Decimal("0")
                if not current_price:
                    continue
                market_value_native = holding.quantity * current_price

            # Convert to USD
            if asset_currency != "USD":
                rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
                market_value_usd = (
                    market_value_native * rate_to_usd if rate_to_usd else market_value_native
                )
            else:
                market_value_usd = market_value_native

            total_value_usd += market_value_usd

    # Convert from USD to portfolio's default currency
    if portfolio.default_currency != "USD":
        rate = CurrencyService.get_exchange_rate(db, "USD", portfolio.default_currency)
        total_value = total_value_usd * rate if rate else total_value_usd
    else:
        total_value = total_value_usd

    return float(total_value)


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

    account_count = (
        db.query(Account).filter(Account.portfolio_id == portfolio.id).count()
    )
    return PortfolioWithAccountCount(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        description=portfolio.description,
        default_currency=portfolio.default_currency,
        is_default=portfolio.is_default,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        account_count=account_count,
    )


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


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a portfolio (must belong to user).
    Returns error if portfolio has accounts or is the user's only portfolio.
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

    # Check if this is the user's only portfolio
    portfolio_count = (
        db.query(Portfolio).filter(Portfolio.user_id == current_user.id).count()
    )
    if portfolio_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your only portfolio",
        )

    # Check if portfolio has accounts
    account_count = (
        db.query(Account).filter(Account.portfolio_id == portfolio_id).count()
    )
    if account_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete portfolio with {account_count} account(s). Move or delete accounts first.",
        )

    db.delete(db_portfolio)
    db.commit()
    return None


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
    # Find the portfolio to set as default
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

    # Unset any existing default portfolio for this user
    db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.is_default == True,  # noqa: E712
    ).update({"is_default": False})

    # Set the selected portfolio as default
    db_portfolio.is_default = True
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio
