"""Tests for CashBalanceRepository."""

from datetime import date
from decimal import Decimal

from app.models import DailyCashBalance
from app.services.repositories.cash_balance_repository import CashBalanceRepository


class TestCashBalanceRepository:
    """Test cases for CashBalanceRepository."""

    def test_find_latest_per_currency_returns_most_recent(self, db, test_account):
        """Returns the most recent balance per currency on or before as_of_date."""
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("1000.00"),
                date=date(2024, 6, 10),
            )
        )
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("1500.00"),
                date=date(2024, 6, 15),
            )
        )
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="ILS",
                balance=Decimal("5000.00"),
                date=date(2024, 6, 12),
            )
        )
        db.commit()

        repo = CashBalanceRepository(db)
        results = repo.find_latest_per_currency(test_account.id, date(2024, 6, 15))
        balances = {b.currency: b for b in results}

        assert len(balances) == 2
        assert balances["USD"].balance == Decimal("1500.00")
        assert balances["ILS"].balance == Decimal("5000.00")

    def test_find_latest_per_currency_empty_when_no_data(self, db, test_account):
        """Returns empty when no balances exist."""
        repo = CashBalanceRepository(db)
        results = repo.find_latest_per_currency(test_account.id, date(2024, 6, 15))
        assert len(results) == 0

    def test_find_latest_per_currency_respects_as_of_date(self, db, test_account):
        """Excludes balances after as_of_date."""
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("1000.00"),
                date=date(2024, 6, 10),
            )
        )
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("2000.00"),
                date=date(2024, 6, 20),
            )
        )
        db.commit()

        repo = CashBalanceRepository(db)
        results = repo.find_latest_per_currency(test_account.id, date(2024, 6, 15))
        assert len(results) == 1
        assert results[0].balance == Decimal("1000.00")

    def test_find_by_account_and_date_range(self, db, test_account):
        """Returns balances within date range."""
        for day in [5, 10, 15, 20, 25]:
            db.add(
                DailyCashBalance(
                    account_id=test_account.id,
                    currency="USD",
                    balance=Decimal(str(day * 100)),
                    date=date(2024, 6, day),
                )
            )
        db.commit()

        repo = CashBalanceRepository(db)
        results = repo.find_by_account_and_date_range(
            test_account.id, date(2024, 6, 10), date(2024, 6, 20)
        )
        assert len(results) == 3

    def test_find_by_account_and_date_range_empty(self, db, test_account):
        """Returns empty when no balances in range."""
        repo = CashBalanceRepository(db)
        results = repo.find_by_account_and_date_range(
            test_account.id, date(2024, 1, 1), date(2024, 1, 5)
        )
        assert len(results) == 0

    def test_find_latest_per_currency_before_date(self, db, test_account):
        """Returns most recent balance strictly before the given date."""
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("1000.00"),
                date=date(2024, 6, 10),
            )
        )
        db.add(
            DailyCashBalance(
                account_id=test_account.id,
                currency="USD",
                balance=Decimal("1500.00"),
                date=date(2024, 6, 15),
            )
        )
        db.commit()

        repo = CashBalanceRepository(db)
        # Strict before: date(2024, 6, 15) should NOT include 6/15 itself
        results = repo.find_latest_per_currency_before_date(
            test_account.id, date(2024, 6, 15)
        )
        assert len(results) == 1
        assert results[0].balance == Decimal("1000.00")
