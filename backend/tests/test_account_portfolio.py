"""Tests for Account-Portfolio relationship."""

from app.models.account import Account
from app.models.portfolio import Portfolio


def test_account_has_portfolio_id():
    """Test that Account model has portfolio_id field."""
    # This tests the model definition
    assert hasattr(Account, "portfolio_id")


def test_portfolio_has_accounts_relationship():
    """Test that Portfolio has accounts relationship."""
    assert hasattr(Portfolio, "accounts")
