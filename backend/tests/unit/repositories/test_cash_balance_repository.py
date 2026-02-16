"""Tests for CashBalanceRepository.create."""

from datetime import date
from decimal import Decimal

from app.models.daily_cash_balance import DailyCashBalance
from app.services.repositories import CashBalanceRepository


class TestCashBalanceRepositoryCreate:
    def test_create_cash_balance(self, db, test_account):
        """create() persists a DailyCashBalance and returns it."""
        repo = CashBalanceRepository(db)
        result = repo.create(
            account_id=test_account.id,
            balance_date=date(2026, 1, 15),
            currency="USD",
            balance=Decimal("8368.50"),
            activity="Synthetic snapshot",
            broker_source_id=None,
        )

        assert result.id is not None
        assert result.currency == "USD"
        assert result.balance == Decimal("8368.50")

        # Verify it's in the DB
        found = db.query(DailyCashBalance).filter(DailyCashBalance.id == result.id).first()
        assert found is not None
