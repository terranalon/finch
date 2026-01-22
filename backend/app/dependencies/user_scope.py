"""Helper functions for user-scoped queries."""

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.user import User


def get_user_portfolio_ids(user: User) -> list[str]:
    """Get all portfolio IDs for a user."""
    return [p.id for p in user.portfolios]


def get_user_account_ids(user: User, db: Session, portfolio_id: str | None = None) -> list[int]:
    """
    Get all account IDs belonging to user's portfolios.

    Args:
        user: The current authenticated user
        db: Database session
        portfolio_id: Optional portfolio ID to filter by. If provided, only returns
                      accounts in that portfolio (must belong to user).
    """
    portfolio_ids = get_user_portfolio_ids(user)
    if not portfolio_ids:
        return []

    # If portfolio_id is specified, validate it belongs to user
    if portfolio_id:
        if portfolio_id not in portfolio_ids:
            return []  # Portfolio doesn't belong to user
        portfolio_ids = [portfolio_id]

    accounts = db.query(Account.id).filter(Account.portfolio_id.in_(portfolio_ids)).all()
    return [a[0] for a in accounts]


def validate_user_portfolio(user: User, db: Session, portfolio_id: str) -> Portfolio | None:
    """
    Validate that portfolio belongs to user and return it.

    Returns None if portfolio doesn't exist or doesn't belong to user.
    """
    return (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
        .first()
    )


def get_user_account(user: User, db: Session, account_id: int) -> Account | None:
    """Get account if it belongs to user (or any active account for service accounts)."""
    # Service accounts can access any active account for automated imports
    if user.is_service_account:
        return (
            db.query(Account)
            .filter(Account.id == account_id, Account.is_active == True)  # noqa: E712
            .first()
        )

    # Regular users: verify ownership via portfolio relationship
    portfolio_ids = get_user_portfolio_ids(user)
    if not portfolio_ids:
        return None

    return (
        db.query(Account)
        .filter(Account.id == account_id, Account.portfolio_id.in_(portfolio_ids))
        .first()
    )


def get_broker_credentials(account: Account, broker_key: str) -> tuple[str | None, str | None]:
    """Extract API credentials from account metadata for a given broker."""
    if not account.meta_data or broker_key not in account.meta_data:
        return None, None
    creds = account.meta_data[broker_key]
    return creds.get("api_key"), creds.get("api_secret")
