"""Tests for Account-Portfolio many-to-many relationship."""

from app.models.account import Account
from app.models.portfolio import Portfolio


def test_account_has_portfolios_relationship():
    """Test that Account model has portfolios relationship (many-to-many)."""
    assert hasattr(Account, "portfolios")


def test_portfolio_has_accounts_relationship():
    """Test that Portfolio has accounts relationship (many-to-many)."""
    assert hasattr(Portfolio, "accounts")
