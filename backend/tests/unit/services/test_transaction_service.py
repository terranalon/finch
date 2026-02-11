"""Tests for TransactionService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models import Holding, HoldingLot
from app.services.portfolio.transaction_service import TransactionService
from app.services.portfolio.transaction_types import (
    InsufficientQuantityError,
    InvalidTransactionTypeError,
    NoOpenLotsError,
    TransactionError,
)


class TestValidateTransactionType:
    def test_accepts_valid_types(self, db):
        svc = TransactionService(db)
        for t in ["Buy", "Sell", "Dividend", "Split", "Merger", "Transfer"]:
            svc.validate_transaction_type(t)

    def test_rejects_invalid_type(self, db):
        svc = TransactionService(db)
        with pytest.raises(InvalidTransactionTypeError):
            svc.validate_transaction_type("InvalidType")


class TestFindOrCreateHolding:
    def test_creates_new_holding(self, db, test_account, test_asset):
        svc = TransactionService(db)
        holding, created = svc.find_or_create_holding(test_account.id, test_asset.id)
        assert created is True
        assert holding.account_id == test_account.id
        assert holding.asset_id == test_asset.id
        assert holding.quantity == Decimal("0")

    def test_returns_existing_holding(self, db, test_holding):
        svc = TransactionService(db)
        holding, created = svc.find_or_create_holding(
            test_holding.account_id, test_holding.asset_id
        )
        assert created is False
        assert holding.id == test_holding.id


class TestProcessBuy:
    def test_creates_lot_and_updates_holding(self, db, test_holding):
        svc = TransactionService(db)
        result = svc.process_buy(
            test_holding,
            quantity=Decimal("5"),
            price_per_unit=Decimal("100"),
            fees=Decimal("10"),
            purchase_date=date(2024, 1, 15),
        )
        assert result.new_quantity == Decimal("15.0")  # 10 + 5
        assert result.new_cost_basis == Decimal("1910.00")  # 1400 + (5*100+10)
        assert result.lot_id is not None

        # Verify lot was created
        lot = db.query(HoldingLot).filter(HoldingLot.id == result.lot_id).first()
        assert lot.quantity == Decimal("5")
        assert lot.remaining_quantity == Decimal("5")
        assert lot.cost_per_unit == Decimal("100")
        assert lot.is_closed is False

    def test_activates_inactive_holding(self, db, test_account, test_asset):
        holding = Holding(
            account_id=test_account.id,
            asset_id=test_asset.id,
            quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            is_active=False,
        )
        db.add(holding)
        db.flush()

        svc = TransactionService(db)
        svc.process_buy(
            holding,
            quantity=Decimal("10"),
            price_per_unit=Decimal("50"),
            fees=Decimal("0"),
            purchase_date=date(2024, 1, 1),
        )
        assert holding.is_active is True
        assert holding.closed_at is None

    def test_rejects_missing_quantity(self, db, test_holding):
        svc = TransactionService(db)
        with pytest.raises(TransactionError):
            svc.process_buy(
                test_holding,
                quantity=None,
                price_per_unit=Decimal("100"),
                fees=Decimal("0"),
                purchase_date=date(2024, 1, 1),
            )

    def test_rejects_missing_price(self, db, test_holding):
        svc = TransactionService(db)
        with pytest.raises(TransactionError):
            svc.process_buy(
                test_holding,
                quantity=Decimal("5"),
                price_per_unit=None,
                fees=Decimal("0"),
                purchase_date=date(2024, 1, 1),
            )


class TestProcessSell:
    @pytest.fixture
    def holding_with_lots(self, db, test_account, test_asset):
        """Create a holding with two FIFO lots."""
        holding = Holding(
            account_id=test_account.id,
            asset_id=test_asset.id,
            quantity=Decimal("15"),
            cost_basis=Decimal("1400"),
            is_active=True,
        )
        db.add(holding)
        db.flush()

        lot1 = HoldingLot(
            holding_id=holding.id,
            quantity=Decimal("10"),
            remaining_quantity=Decimal("10"),
            cost_per_unit=Decimal("80"),
            purchase_date=date(2024, 1, 1),
            purchase_price_original=Decimal("80"),
            fees=Decimal("0"),
            is_closed=False,
        )
        lot2 = HoldingLot(
            holding_id=holding.id,
            quantity=Decimal("5"),
            remaining_quantity=Decimal("5"),
            cost_per_unit=Decimal("120"),
            purchase_date=date(2024, 2, 1),
            purchase_price_original=Decimal("120"),
            fees=Decimal("0"),
            is_closed=False,
        )
        db.add_all([lot1, lot2])
        db.flush()
        return holding, lot1, lot2

    def test_fifo_sells_oldest_lot_first(self, db, holding_with_lots):
        holding, lot1, lot2 = holding_with_lots
        svc = TransactionService(db)
        result = svc.process_sell(holding, quantity=Decimal("8"))

        assert result.new_quantity == Decimal("7")  # 15 - 8
        assert result.total_cost_basis_sold == Decimal("640")  # 8 * 80
        assert result.is_closed is False

        db.refresh(lot1)
        assert lot1.remaining_quantity == Decimal("2")
        assert lot1.is_closed is False

    def test_fifo_closes_exhausted_lot(self, db, holding_with_lots):
        holding, lot1, lot2 = holding_with_lots
        svc = TransactionService(db)
        result = svc.process_sell(holding, quantity=Decimal("12"))

        # 10 from lot1 (closed) + 2 from lot2
        assert result.new_quantity == Decimal("3")
        assert result.total_cost_basis_sold == Decimal("1040")  # 10*80 + 2*120
        assert result.is_closed is False

        db.refresh(lot1)
        assert lot1.remaining_quantity == Decimal("0")
        assert lot1.is_closed is True

        db.refresh(lot2)
        assert lot2.remaining_quantity == Decimal("3")
        assert lot2.is_closed is False

    def test_sell_all_marks_inactive(self, db, holding_with_lots):
        holding, lot1, lot2 = holding_with_lots
        svc = TransactionService(db)
        result = svc.process_sell(holding, quantity=Decimal("15"))

        assert result.new_quantity == Decimal("0")
        assert result.is_closed is True
        assert holding.is_active is False

    def test_insufficient_quantity_raises(self, db, holding_with_lots):
        holding, _, _ = holding_with_lots
        svc = TransactionService(db)
        with pytest.raises(InsufficientQuantityError):
            svc.process_sell(holding, quantity=Decimal("20"))

    def test_rejects_missing_quantity(self, db, holding_with_lots):
        holding, _, _ = holding_with_lots
        svc = TransactionService(db)
        with pytest.raises(TransactionError):
            svc.process_sell(holding, quantity=None)

    def test_no_open_lots_raises(self, db, test_account, test_asset):
        holding = Holding(
            account_id=test_account.id,
            asset_id=test_asset.id,
            quantity=Decimal("10"),
            cost_basis=Decimal("1000"),
            is_active=True,
        )
        db.add(holding)
        db.flush()

        svc = TransactionService(db)
        with pytest.raises(NoOpenLotsError):
            svc.process_sell(holding, quantity=Decimal("5"))
