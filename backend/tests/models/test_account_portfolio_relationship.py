"""Tests for many-to-many Account-Portfolio relationship."""

from app.models.account import Account
from app.models.portfolio import Portfolio


def test_account_has_portfolios_relationship():
    """Account model should have 'portfolios' as a list relationship."""
    assert hasattr(Account, "portfolios")


def test_portfolio_has_accounts_relationship():
    """Portfolio model should have 'accounts' as a list relationship."""
    assert hasattr(Portfolio, "accounts")


def test_account_can_belong_to_multiple_portfolios(db_session, test_user):
    """An account can be linked to multiple portfolios."""
    portfolio1 = Portfolio(name="All", user_id=test_user.id)
    portfolio2 = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    account = Account(
        name="Kraken",
        institution="Kraken",
        account_type="CryptoExchange",
        currency="USD",
    )
    account.portfolios = [portfolio1, portfolio2]
    db_session.add(account)
    db_session.commit()

    # Verify bidirectional relationship
    assert len(account.portfolios) == 2
    assert account in portfolio1.accounts
    assert account in portfolio2.accounts


def test_portfolio_can_have_multiple_accounts(db_session, test_user):
    """A portfolio can contain multiple accounts."""
    portfolio = Portfolio(name="All", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.flush()

    account1 = Account(
        name="Kraken",
        institution="Kraken",
        account_type="CryptoExchange",
        currency="USD",
    )
    account2 = Account(
        name="IBKR",
        institution="Interactive Brokers",
        account_type="Brokerage",
        currency="USD",
    )
    portfolio.accounts = [account1, account2]
    db_session.add_all([account1, account2])
    db_session.commit()

    # Verify relationship persists after fresh query
    db_session.expire_all()
    refreshed_portfolio = db_session.get(Portfolio, portfolio.id)
    assert len(refreshed_portfolio.accounts) == 2
    account_names = {a.name for a in refreshed_portfolio.accounts}
    assert account_names == {"Kraken", "IBKR"}
