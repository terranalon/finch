"""Tests for TransactionRepository new methods."""

from datetime import date
from decimal import Decimal

from app.models import Transaction
from app.services.repositories.transaction_repository import TransactionRepository


class TestTransactionRepositoryNewMethods:
    """Test cases for new TransactionRepository methods."""

    def test_find_with_holdings_and_assets_by_account(self, db, test_holding, test_asset):
        """Returns transactions joined with holdings and assets."""
        txn = Transaction(
            holding_id=test_holding.id,
            type="Buy",
            date=date(2024, 6, 15),
            quantity=Decimal("10"),
            price_per_unit=Decimal("150.00"),
            amount=Decimal("1500.00"),
        )
        db.add(txn)
        db.commit()

        repo = TransactionRepository(db)
        results = repo.find_with_holdings_and_assets_by_account(test_holding.account_id)
        assert len(results) == 1
        txn_row, holding_row, asset_row = results[0]
        assert txn_row.type == "Buy"
        assert asset_row.symbol == test_asset.symbol

    def test_find_with_holdings_and_assets_by_account_with_date_filter(
        self, db, test_holding, test_asset
    ):
        """Filters transactions by as_of_date."""
        db.add(
            Transaction(
                holding_id=test_holding.id,
                type="Buy",
                date=date(2024, 6, 10),
                quantity=Decimal("10"),
                price_per_unit=Decimal("150.00"),
                amount=Decimal("1500.00"),
            )
        )
        db.add(
            Transaction(
                holding_id=test_holding.id,
                type="Buy",
                date=date(2024, 6, 20),
                quantity=Decimal("5"),
                price_per_unit=Decimal("155.00"),
                amount=Decimal("775.00"),
            )
        )
        db.commit()

        repo = TransactionRepository(db)
        results = repo.find_with_holdings_and_assets_by_account(
            test_holding.account_id, as_of_date=date(2024, 6, 15)
        )
        assert len(results) == 1
        assert results[0][0].date == date(2024, 6, 10)

    def test_count_by_account_with_transactions(self, db, test_holding):
        """Returns count > 0 when transactions exist."""
        db.add(
            Transaction(
                holding_id=test_holding.id,
                type="Buy",
                date=date(2024, 6, 15),
                quantity=Decimal("10"),
                price_per_unit=Decimal("150.00"),
                amount=Decimal("1500.00"),
            )
        )
        db.commit()

        repo = TransactionRepository(db)
        count = repo.count_by_account(test_holding.account_id)
        assert count > 0

    def test_count_by_account_no_transactions(self, db, test_account):
        """Returns 0 when no transactions exist."""
        repo = TransactionRepository(db)
        count = repo.count_by_account(test_account.id)
        assert count == 0

    def test_find_first_by_holding_found(self, db, test_holding):
        """Returns first transaction for a holding."""
        db.add(
            Transaction(
                holding_id=test_holding.id,
                type="Buy",
                date=date(2024, 6, 15),
                quantity=Decimal("10"),
                price_per_unit=Decimal("150.00"),
                amount=Decimal("1500.00"),
            )
        )
        db.commit()

        repo = TransactionRepository(db)
        result = repo.find_first_by_holding(test_holding.id)
        assert result is not None
        assert result.type == "Buy"

    def test_find_first_by_holding_not_found(self, db, test_holding):
        """Returns None when no transactions for holding."""
        repo = TransactionRepository(db)
        result = repo.find_first_by_holding(test_holding.id)
        assert result is None
