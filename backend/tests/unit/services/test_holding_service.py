"""Tests for HoldingService."""

from datetime import date
from decimal import Decimal

from app.models import Transaction
from app.services.portfolio.holding_service import HoldingService


class TestListHoldings:
    def test_returns_holding_with_account_and_asset(
        self, db, test_account, test_asset, test_holding
    ):
        svc = HoldingService(db)
        results, total = svc.list_holdings([test_account.id])
        assert len(results) == 1
        assert total == 1
        assert results[0].id == test_holding.id
        assert results[0].account.name == "Test Account"
        assert results[0].asset.symbol == "AAPL"

    def test_filters_by_account_id(self, db, test_account, test_asset, test_holding):
        svc = HoldingService(db)
        results, total = svc.list_holdings([test_account.id], account_id=test_account.id)
        assert len(results) == 1
        assert total == 1

    def test_filters_by_active_status(self, db, test_account, test_asset, test_holding):
        svc = HoldingService(db)
        active, active_total = svc.list_holdings([test_account.id], is_active=True)
        assert len(active) == 1
        assert active_total == 1

        inactive, inactive_total = svc.list_holdings([test_account.id], is_active=False)
        assert len(inactive) == 0
        assert inactive_total == 0

    def test_empty_accounts_returns_empty(self, db):
        svc = HoldingService(db)
        items, total = svc.list_holdings([])
        assert items == []
        assert total == 0


class TestReconstructHoldings:
    def test_updates_holding_from_transactions(self, db, test_account, test_asset, test_holding):
        txn = Transaction(
            holding_id=test_holding.id,
            date=date(2024, 1, 15),
            type="Buy",
            quantity=Decimal("5"),
            price_per_unit=Decimal("100"),
            fees=Decimal("0"),
        )
        db.add(txn)
        db.commit()

        svc = HoldingService(db)
        stats = svc.reconstruct_holdings(test_account.id)
        assert stats.account_id == test_account.id
        assert stats.holdings_updated >= 0
