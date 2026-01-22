"""Transactions API router - CRUD operations with business logic."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Asset, Holding, HoldingLot, Transaction
from app.models.user import User
from app.schemas.transaction import Transaction as TransactionSchema
from app.schemas.transaction import TransactionCreate, TransactionCreateRequest, TransactionUpdate

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionSchema])
async def list_transactions(
    holding_id: int | None = None,
    account_id: int | None = None,
    transaction_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of transactions with optional filters (filtered by user's accounts).

    Filters:
    - holding_id: Filter by specific holding
    - account_id: Filter by account (via holding)
    - transaction_type: Filter by type (Buy, Sell, Dividend, etc.)
    - start_date: Transactions on or after this date
    - end_date: Transactions on or before this date
    - portfolio_id: Filter by specific portfolio (must belong to user)
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    # Always join with Holding to filter by user's accounts
    query = db.query(Transaction).join(Holding).filter(Holding.account_id.in_(allowed_account_ids))

    if holding_id:
        query = query.filter(Transaction.holding_id == holding_id)

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        query = query.filter(Holding.account_id == account_id)

    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)

    if start_date:
        query = query.filter(Transaction.date >= start_date)

    if end_date:
        query = query.filter(Transaction.date <= end_date)

    # Order by date descending (most recent first)
    query = query.order_by(desc(Transaction.date), desc(Transaction.id))

    transactions = query.offset(offset).limit(limit).all()
    return transactions


@router.get("/{transaction_id}", response_model=TransactionSchema)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific transaction by ID (must belong to user's accounts)."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    # Verify transaction belongs to user's account
    holding = db.query(Holding).filter(Holding.id == transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    return transaction


@router.post("", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: TransactionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new transaction and apply business logic (account must belong to user).

    Accepts account_id + asset_id and automatically finds or creates the holding.

    Business Logic:
    - Buy: Creates or updates holding, creates new holding lot
    - Sell: Updates holding, reduces lots using FIFO
    - Dividend: Records transaction only
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if transaction.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {transaction.account_id} not found",
        )

    # Validate asset exists
    asset = db.query(Asset).filter(Asset.id == transaction.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {transaction.asset_id} not found",
        )

    # Validate transaction type
    valid_types = ["Buy", "Sell", "Dividend", "Split", "Merger", "Transfer"]
    if transaction.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}",
        )

    # Find or create holding for this account + asset combination
    holding = (
        db.query(Holding)
        .filter(
            Holding.account_id == transaction.account_id, Holding.asset_id == transaction.asset_id
        )
        .first()
    )

    if not holding:
        # Create new holding
        holding = Holding(
            account_id=transaction.account_id,
            asset_id=transaction.asset_id,
            quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            is_active=False,
        )
        db.add(holding)
        db.flush()  # Get the holding ID

    # Create the transaction record with the holding_id
    transaction_data = transaction.model_dump()
    transaction_data["holding_id"] = holding.id
    transaction_data.pop("account_id")
    transaction_data.pop("asset_id")

    db_transaction = Transaction(**transaction_data)
    db.add(db_transaction)

    # Apply business logic based on transaction type
    if transaction.type == "Buy":
        await _process_buy_transaction(db, holding, transaction)
    elif transaction.type == "Sell":
        await _process_sell_transaction(db, holding, transaction)
    # Dividend and other types just record the transaction

    db.commit()
    db.refresh(db_transaction)

    return db_transaction


@router.put("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing transaction (must belong to user's accounts).

    Note: Updating transactions can affect holdings and lots.
    For simplicity, this endpoint only updates the transaction record.
    For complex scenarios, delete and recreate the transaction.
    """
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    # Verify transaction belongs to user's account
    holding = db.query(Holding).filter(Holding.id == db_transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    # Update only provided fields
    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    db.commit()
    db.refresh(db_transaction)

    return db_transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a transaction (must belong to user's accounts).

    Note: This only deletes the transaction record.
    It does not reverse the effects on holdings/lots.
    """
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    # Verify transaction belongs to user's account
    holding = db.query(Holding).filter(Holding.id == db_transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    db.delete(db_transaction)
    db.commit()

    return None


# Business Logic Helper Functions


async def _process_buy_transaction(db: Session, holding: Holding, transaction: TransactionCreate):
    """Process a Buy transaction - update holding and create lot."""
    if not transaction.quantity or not transaction.price_per_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buy transactions require quantity and price_per_unit",
        )

    # Calculate cost including fees
    cost = (transaction.quantity * transaction.price_per_unit) + transaction.fees

    # Update holding
    holding.quantity += transaction.quantity
    holding.cost_basis += cost
    holding.is_active = True
    holding.closed_at = None

    # Create new holding lot
    new_lot = HoldingLot(
        holding_id=holding.id,
        quantity=transaction.quantity,
        remaining_quantity=transaction.quantity,
        cost_per_unit=transaction.price_per_unit,
        purchase_date=transaction.date,
        purchase_price_original=transaction.price_per_unit,
        fees=transaction.fees,
        is_closed=False,
    )
    db.add(new_lot)


async def _process_sell_transaction(db: Session, holding: Holding, transaction: TransactionCreate):
    """Process a Sell transaction - update holding and reduce lots using FIFO."""
    if not transaction.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Sell transactions require quantity"
        )

    # Validate sufficient quantity
    if holding.quantity < transaction.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient quantity. Holding has {holding.quantity}, trying to sell {transaction.quantity}",
        )

    # Get lots in FIFO order (oldest first)
    lots = (
        db.query(HoldingLot)
        .filter(
            HoldingLot.holding_id == holding.id,
            HoldingLot.is_closed.is_(False),
            HoldingLot.remaining_quantity > 0,
        )
        .order_by(HoldingLot.purchase_date, HoldingLot.id)
        .all()
    )

    if not lots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No open lots found for this holding"
        )

    # Apply FIFO to reduce lots
    remaining_to_sell = transaction.quantity
    total_cost_basis_sold = Decimal("0")

    for lot in lots:
        if remaining_to_sell <= 0:
            break

        if lot.remaining_quantity <= remaining_to_sell:
            # Sell entire lot
            quantity_from_lot = lot.remaining_quantity
            lot.remaining_quantity = Decimal("0")
            lot.is_closed = True
        else:
            # Partially sell from lot
            quantity_from_lot = remaining_to_sell
            lot.remaining_quantity -= quantity_from_lot

        # Calculate cost basis for this portion
        cost_basis_from_lot = quantity_from_lot * lot.cost_per_unit
        total_cost_basis_sold += cost_basis_from_lot
        remaining_to_sell -= quantity_from_lot

    if remaining_to_sell > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not allocate all shares to lots. {remaining_to_sell} shares remaining.",
        )

    # Update holding
    holding.quantity -= transaction.quantity
    holding.cost_basis -= total_cost_basis_sold

    # If quantity reaches zero, mark holding as inactive
    if holding.quantity == 0:
        holding.is_active = False
        holding.closed_at = (
            db.query(Transaction)
            .filter(Transaction.holding_id == holding.id)
            .order_by(desc(Transaction.date))
            .first()
            .date
        )
