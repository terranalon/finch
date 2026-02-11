"""Tests for PortfolioManagementService."""

from decimal import Decimal

import pytest

from app.constants import AssetClass
from app.models import Account, Asset, Holding, Portfolio
from app.services.portfolio.portfolio_management_service import (
    PortfolioManagementService,
)


class TestCalculatePortfolioValue:
    def test_single_equity_holding(self, db, test_portfolio, test_account, test_asset, test_holding):
        svc = PortfolioManagementService(db)
        value = svc.calculate_portfolio_value(test_portfolio)
        # test_holding: qty=10, test_asset: last_fetched_price=150, currency=USD
        assert value == pytest.approx(1500.0)

    def test_empty_portfolio(self, db, test_portfolio):
        svc = PortfolioManagementService(db)
        value = svc.calculate_portfolio_value(test_portfolio)
        assert value == 0.0

    def test_skips_inactive_holdings(self, db, test_portfolio, test_account, test_asset):
        holding = Holding(
            account_id=test_account.id,
            asset_id=test_asset.id,
            quantity=Decimal("100"),
            cost_basis=Decimal("10000"),
            is_active=False,
        )
        db.add(holding)
        db.commit()

        svc = PortfolioManagementService(db)
        value = svc.calculate_portfolio_value(test_portfolio)
        assert value == 0.0

    def test_cash_uses_quantity_as_value(self, db, test_portfolio, test_account):
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class=AssetClass.CASH,
            currency="USD",
        )
        db.add(cash_asset)
        db.flush()

        cash_holding = Holding(
            account_id=test_account.id,
            asset_id=cash_asset.id,
            quantity=Decimal("5000"),
            cost_basis=Decimal("0"),
            is_active=True,
        )
        db.add(cash_holding)
        db.commit()

        svc = PortfolioManagementService(db)
        value = svc.calculate_portfolio_value(test_portfolio)
        assert value == pytest.approx(5000.0)


class TestCategorizeAccounts:
    def test_exclusive_account(self, db, test_portfolio, test_account):
        svc = PortfolioManagementService(db)
        exclusive, shared = svc.categorize_accounts_for_deletion(test_portfolio)
        assert len(exclusive) == 1
        assert exclusive[0].id == test_account.id
        assert len(shared) == 0

    def test_shared_account(self, db, test_user, test_portfolio, test_account):
        other_portfolio = Portfolio(
            name="Other Portfolio",
            user_id=str(test_user.id),
            default_currency="USD",
        )
        db.add(other_portfolio)
        db.flush()
        test_account.portfolios.append(other_portfolio)
        db.commit()

        svc = PortfolioManagementService(db)
        exclusive, shared = svc.categorize_accounts_for_deletion(test_portfolio)
        assert len(exclusive) == 0
        assert len(shared) == 1
        assert shared[0].id == test_account.id


class TestDeletePortfolioCascade:
    def test_deletes_exclusive_accounts(self, db, test_portfolio, test_account):
        account_id = test_account.id
        svc = PortfolioManagementService(db)
        svc.delete_portfolio_cascade(test_portfolio)
        db.flush()

        assert db.query(Account).filter(Account.id == account_id).first() is None
        assert db.query(Portfolio).filter(Portfolio.id == test_portfolio.id).first() is None

    def test_unlinks_shared_accounts(self, db, test_user, test_portfolio, test_account):
        other_portfolio = Portfolio(
            name="Other Portfolio",
            user_id=str(test_user.id),
            default_currency="USD",
        )
        db.add(other_portfolio)
        db.flush()
        test_account.portfolios.append(other_portfolio)
        db.commit()

        account_id = test_account.id
        svc = PortfolioManagementService(db)
        svc.delete_portfolio_cascade(test_portfolio)
        db.flush()

        # Account still exists, but no longer linked to deleted portfolio
        account = db.query(Account).filter(Account.id == account_id).first()
        assert account is not None
        assert test_portfolio not in account.portfolios
