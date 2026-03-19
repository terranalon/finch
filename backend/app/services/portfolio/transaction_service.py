"""Transaction business logic - buy/sell processing with FIFO lot allocation."""

from datetime import date
from decimal import Decimal

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Holding, HoldingLot, Transaction
from app.services.portfolio.transaction_types import (
    BuyResult,
    InsufficientQuantityError,
    InvalidTransactionTypeError,
    NoOpenLotsError,
    SellResult,
    TransactionError,
)
from app.services.repositories import HoldingRepository

VALID_TRANSACTION_TYPES = ["Buy", "Sell", "Dividend", "Split", "Merger", "Transfer"]


class TransactionService:
    """Processes buy/sell transactions with FIFO lot management."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._holding_repo = HoldingRepository(db)

    def validate_transaction_type(self, transaction_type: str) -> None:
        if transaction_type not in VALID_TRANSACTION_TYPES:
            raise InvalidTransactionTypeError(
                f"Invalid transaction type '{transaction_type}'. "
                f"Must be one of: {', '.join(VALID_TRANSACTION_TYPES)}"
            )

    def find_or_create_holding(self, account_id: int, asset_id: int) -> tuple[Holding, bool]:
        return self._holding_repo.find_or_create(account_id, asset_id)

    def process_buy(
        self,
        holding: Holding,
        quantity: Decimal | None,
        price_per_unit: Decimal | None,
        fees: Decimal,
        purchase_date: date,
    ) -> BuyResult:
        if not quantity or not price_per_unit:
            raise TransactionError("Buy transactions require quantity and price_per_unit")

        cost = (quantity * price_per_unit) + fees

        holding.quantity += quantity
        holding.cost_basis += cost
        holding.is_active = True
        holding.closed_at = None

        new_lot = HoldingLot(
            holding_id=holding.id,
            quantity=quantity,
            remaining_quantity=quantity,
            cost_per_unit=price_per_unit,
            purchase_date=purchase_date,
            purchase_price_original=price_per_unit,
            fees=fees,
            is_closed=False,
        )
        self._db.add(new_lot)
        self._db.flush()

        return BuyResult(
            holding_id=holding.id,
            new_quantity=holding.quantity,
            new_cost_basis=holding.cost_basis,
            lot_id=new_lot.id,
        )

    def process_sell(
        self,
        holding: Holding,
        quantity: Decimal | None,
    ) -> SellResult:
        if not quantity:
            raise TransactionError("Sell transactions require quantity")

        if holding.quantity < quantity:
            raise InsufficientQuantityError(
                f"Insufficient quantity. Holding has {holding.quantity}, trying to sell {quantity}"
            )

        lots = (
            self._db.query(HoldingLot)
            .filter(
                HoldingLot.holding_id == holding.id,
                HoldingLot.is_closed.is_(False),
                HoldingLot.remaining_quantity > 0,
            )
            .order_by(HoldingLot.purchase_date, HoldingLot.id)
            .all()
        )

        if not lots:
            raise NoOpenLotsError("No open lots found for this holding")

        remaining_to_sell = quantity
        total_cost_basis_sold = Decimal("0")

        for lot in lots:
            if remaining_to_sell <= 0:
                break

            if lot.remaining_quantity <= remaining_to_sell:  # ty: ignore[unsupported-operator] — remaining_quantity is non-null for open lots
                quantity_from_lot = lot.remaining_quantity
                lot.remaining_quantity = Decimal("0")
                lot.is_closed = True
            else:
                quantity_from_lot = remaining_to_sell
                lot.remaining_quantity -= quantity_from_lot  # ty: ignore[unsupported-operator] — remaining_quantity is non-null for open lots

            # Include proportional buy fees in cost basis (matches _consume_lots in
            # realized_pnl_service and PortfolioReconstructionService FIFO logic)
            lot_cost = quantity_from_lot * lot.cost_per_unit  # ty: ignore[unsupported-operator] — quantity_from_lot is always Decimal
            if lot.quantity > 0 and lot.fees > 0:
                lot_cost += (quantity_from_lot / lot.quantity) * lot.fees  # ty: ignore[unsupported-operator]
            total_cost_basis_sold += lot_cost
            remaining_to_sell -= quantity_from_lot  # ty: ignore[unsupported-operator] — quantity_from_lot is always Decimal from either branch

        if remaining_to_sell > 0:
            raise InsufficientQuantityError(
                f"Could not allocate all shares to lots. {remaining_to_sell} shares remaining."
            )

        holding.quantity -= quantity
        holding.cost_basis -= total_cost_basis_sold

        is_closed = holding.quantity == 0
        if is_closed:
            holding.is_active = False
            last_txn = (
                self._db.query(Transaction)
                .filter(Transaction.holding_id == holding.id)
                .order_by(desc(Transaction.date))
                .first()
            )
            if last_txn:
                holding.closed_at = last_txn.date  # ty: ignore[invalid-assignment] — SQLAlchemy descriptor allows assignment

        self._db.flush()

        return SellResult(
            holding_id=holding.id,
            new_quantity=holding.quantity,
            new_cost_basis=holding.cost_basis,
            total_cost_basis_sold=total_cost_basis_sold,
            is_closed=is_closed,
        )
