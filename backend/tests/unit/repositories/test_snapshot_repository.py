"""Tests for SnapshotRepository."""

from datetime import date, timedelta
from decimal import Decimal

from app.models import HistoricalSnapshot
from app.services.repositories.snapshot_repository import SnapshotRepository


class TestSnapshotRepository:
    """Test cases for SnapshotRepository."""

    def test_find_by_account_and_date_found(self, db, test_account):
        """Returns matching snapshot."""
        snapshot = HistoricalSnapshot(
            account_id=test_account.id,
            date=date(2024, 6, 15),
            total_value_usd=Decimal("10000.00"),
            total_value_ils=Decimal("37000.00"),
        )
        db.add(snapshot)
        db.commit()

        repo = SnapshotRepository(db)
        found = repo.find_by_account_and_date(test_account.id, date(2024, 6, 15))
        assert found is not None
        assert found.total_value_usd == Decimal("10000.00")

    def test_find_by_account_and_date_returns_none(self, db, test_account):
        """Returns None when no snapshot exists."""
        repo = SnapshotRepository(db)
        found = repo.find_by_account_and_date(test_account.id, date(2024, 1, 1))
        assert found is None

    def test_sum_values_by_date(self, db, test_user, test_portfolio):
        """Sums values across multiple accounts on a date."""
        from app.models import Account

        account1 = Account(
            name="Account 1",
            account_type="brokerage",
            institution="Test",
            currency="USD",
        )
        account1.portfolios.append(test_portfolio)
        account2 = Account(
            name="Account 2",
            account_type="brokerage",
            institution="Test",
            currency="USD",
        )
        account2.portfolios.append(test_portfolio)
        db.add_all([account1, account2])
        db.flush()

        db.add(
            HistoricalSnapshot(
                account_id=account1.id,
                date=date(2024, 6, 15),
                total_value_usd=Decimal("5000.00"),
                total_value_ils=Decimal("18500.00"),
            )
        )
        db.add(
            HistoricalSnapshot(
                account_id=account2.id,
                date=date(2024, 6, 15),
                total_value_usd=Decimal("3000.00"),
                total_value_ils=Decimal("11100.00"),
            )
        )
        db.commit()

        repo = SnapshotRepository(db)
        total = repo.sum_values_by_date([account1.id, account2.id], date(2024, 6, 15))
        assert total == Decimal("8000.00")

    def test_sum_values_by_date_returns_none_when_no_data(self, db, test_account):
        """Returns None when no snapshots exist for the date."""
        repo = SnapshotRepository(db)
        total = repo.sum_values_by_date([test_account.id], date(2024, 1, 1))
        assert total is None

    def test_find_aggregated_performance(self, db, test_account):
        """Returns aggregated performance grouped by date."""
        for i in range(5):
            db.add(
                HistoricalSnapshot(
                    account_id=test_account.id,
                    date=date(2024, 6, 10) + timedelta(days=i),
                    total_value_usd=Decimal("10000.00") + Decimal(str(i * 100)),
                    total_value_ils=Decimal("37000.00") + Decimal(str(i * 370)),
                )
            )
        db.commit()

        repo = SnapshotRepository(db)
        rows = repo.find_aggregated_performance([test_account.id], days=3)
        assert len(rows) == 3
        # Most recent first
        assert rows[0].date == date(2024, 6, 14)

    def test_find_by_account_with_date_range(self, db, test_account):
        """Returns snapshots within date range."""
        for i in range(10):
            db.add(
                HistoricalSnapshot(
                    account_id=test_account.id,
                    date=date(2024, 6, 1) + timedelta(days=i),
                    total_value_usd=Decimal("10000.00"),
                    total_value_ils=Decimal("37000.00"),
                )
            )
        db.commit()

        repo = SnapshotRepository(db)
        snapshots = repo.find_by_account(
            test_account.id,
            start_date=date(2024, 6, 3),
            end_date=date(2024, 6, 7),
        )
        assert len(snapshots) == 5

    def test_find_by_account_with_limit(self, db, test_account):
        """Respects limit parameter."""
        for i in range(10):
            db.add(
                HistoricalSnapshot(
                    account_id=test_account.id,
                    date=date(2024, 6, 1) + timedelta(days=i),
                    total_value_usd=Decimal("10000.00"),
                    total_value_ils=Decimal("37000.00"),
                )
            )
        db.commit()

        repo = SnapshotRepository(db)
        snapshots = repo.find_by_account(test_account.id, limit=3)
        assert len(snapshots) == 3

    def test_find_aggregated_portfolio_history(self, db, test_user, test_portfolio):
        """Returns aggregated history across accounts."""
        from app.models import Account

        account1 = Account(
            name="Account A",
            account_type="brokerage",
            institution="Test",
            currency="USD",
        )
        account1.portfolios.append(test_portfolio)
        account2 = Account(
            name="Account B",
            account_type="brokerage",
            institution="Test",
            currency="USD",
        )
        account2.portfolios.append(test_portfolio)
        db.add_all([account1, account2])
        db.flush()

        db.add(
            HistoricalSnapshot(
                account_id=account1.id,
                date=date(2024, 6, 15),
                total_value_usd=Decimal("5000.00"),
                total_value_ils=Decimal("18500.00"),
            )
        )
        db.add(
            HistoricalSnapshot(
                account_id=account2.id,
                date=date(2024, 6, 15),
                total_value_usd=Decimal("3000.00"),
                total_value_ils=Decimal("11100.00"),
            )
        )
        db.commit()

        repo = SnapshotRepository(db)
        rows = repo.find_aggregated_portfolio_history(account_ids=[account1.id, account2.id])
        assert len(rows) == 1
        assert rows[0].total_usd == Decimal("8000.00")

    def test_delete_by_account_and_date_range(self, db, test_account):
        """Deletes snapshots in range and returns count."""
        for i in range(5):
            db.add(
                HistoricalSnapshot(
                    account_id=test_account.id,
                    date=date(2024, 6, 10) + timedelta(days=i),
                    total_value_usd=Decimal("10000.00"),
                    total_value_ils=Decimal("37000.00"),
                )
            )
        db.commit()

        repo = SnapshotRepository(db)
        deleted = repo.delete_by_account_and_date_range(
            test_account.id, date(2024, 6, 11), date(2024, 6, 13)
        )
        assert deleted == 3

    def test_create_persists_snapshot(self, db, test_account):
        """Creates and flushes a new snapshot."""
        repo = SnapshotRepository(db)
        created = repo.create(
            test_account.id,
            date(2024, 7, 1),
            Decimal("15000.00"),
            Decimal("55500.00"),
        )
        assert created.id is not None
        assert created.total_value_usd == Decimal("15000.00")
