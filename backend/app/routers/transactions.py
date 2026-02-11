"""Transactions API router - CRUD operations with business logic."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Asset, Holding, Transaction
from app.models.user import User
from app.schemas.transaction import Transaction as TransactionSchema
from app.schemas.transaction import TransactionCreateRequest, TransactionUpdate
from app.services.portfolio.transaction_service import TransactionService
from app.services.portfolio.transaction_types import TransactionError

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

    query = (
        db.query(Transaction)
        .join(Transaction.holding)
        .filter(Holding.account_id.in_(allowed_account_ids))
    )

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

    query = query.order_by(desc(Transaction.date), desc(Transaction.id))
    return query.offset(offset).limit(limit).all()


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
    allowed_account_ids = get_user_account_ids(current_user, db)
    if transaction.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {transaction.account_id} not found",
        )

    asset = db.query(Asset).filter(Asset.id == transaction.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with id {transaction.asset_id} not found",
        )

    svc = TransactionService(db)
    try:
        svc.validate_transaction_type(transaction.type)
        holding, _ = svc.find_or_create_holding(transaction.account_id, transaction.asset_id)

        transaction_data = transaction.model_dump()
        transaction_data["holding_id"] = holding.id
        transaction_data.pop("account_id")
        transaction_data.pop("asset_id")

        db_transaction = Transaction(**transaction_data)
        db.add(db_transaction)

        if transaction.type == "Buy":
            svc.process_buy(
                holding,
                transaction.quantity,
                transaction.price_per_unit,
                transaction.fees,
                transaction.date,
            )
        elif transaction.type == "Sell":
            svc.process_sell(holding, transaction.quantity)

        db.commit()
        db.refresh(db_transaction)
        return db_transaction

    except TransactionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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

    holding = db.query(Holding).filter(Holding.id == db_transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

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
