"""Tests for portfolio_accounts association table."""

from app.models.portfolio_account import portfolio_accounts


def test_portfolio_accounts_table_exists():
    """Verify the association table has correct columns."""
    columns = {c.name for c in portfolio_accounts.columns}
    assert "portfolio_id" in columns
    assert "account_id" in columns
    assert "added_at" in columns


def test_portfolio_accounts_primary_key():
    """Verify composite primary key on portfolio_id + account_id."""
    pk_columns = [c.name for c in portfolio_accounts.primary_key.columns]
    assert set(pk_columns) == {"portfolio_id", "account_id"}
