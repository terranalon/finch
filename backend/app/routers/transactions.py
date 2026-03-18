"""Transactions API router - CRUD operations with business logic."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.exceptions import BadRequestError, NotFoundError
from app.models import Asset, Holding, Transaction
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import Transaction as TransactionSchema
from app.schemas.transaction import TransactionCreateRequest, TransactionUpdate
from app.services.portfolio.realized_pnl_service import compute_realized_pnl_usd
from app.services.portfolio.transaction_service import TransactionService
from app.services.portfolio.transaction_types import TransactionError

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _load_transaction_with_relations(db: Session, transaction_id: int) -> Transaction:
    """Re-query a transaction with eager-loaded holding, asset, and account."""
    return (
        db.query(Transaction)
        .options(
            joinedload(Transaction.holding).joinedload(Holding.asset),
            joinedload(Transaction.holding).joinedload(Holding.account),
        )
        .filter(Transaction.id == transaction_id)
        .one()
    )


@router.get("", response_model=PaginatedResponse[TransactionSchema])
async def list_transactions(
    holding_id: int | None = None,
    account_id: int | None = None,
    transaction_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of transactions with optional filters (filtered by user's accounts)."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return PaginatedResponse.create(items=[], total=0, skip=skip, limit=limit)

    base_query = (
        db.query(Transaction)
        .join(Transaction.holding)
        .filter(Holding.account_id.in_(allowed_account_ids))
    )

    if holding_id:
        base_query = base_query.filter(Transaction.holding_id == holding_id)

    if account_id:
        if account_id not in allowed_account_ids:
            raise NotFoundError("Account", account_id)
        base_query = base_query.filter(Holding.account_id == account_id)

    if transaction_type:
        base_query = base_query.filter(Transaction.type == transaction_type)

    if start_date:
        base_query = base_query.filter(Transaction.date >= start_date)

    if end_date:
        base_query = base_query.filter(Transaction.date <= end_date)

    base_query = base_query.order_by(desc(Transaction.date), desc(Transaction.id))

    total = base_query.count()
    items = (
        base_query.options(
            contains_eager(Transaction.holding).joinedload(Holding.asset),
            contains_eager(Transaction.holding).joinedload(Holding.account),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    enriched = [TransactionSchema.from_orm_enriched(item) for item in items]

    return PaginatedResponse.create(items=enriched, total=total, skip=skip, limit=limit)


@router.get("/{transaction_id}", response_model=TransactionSchema)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific transaction by ID (must belong to user's accounts)."""
    transaction = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.holding).joinedload(Holding.asset),
            joinedload(Transaction.holding).joinedload(Holding.account),
        )
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not transaction:
        raise NotFoundError("Transaction", transaction_id)

    holding = transaction.holding
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise NotFoundError("Transaction", transaction_id)

    return TransactionSchema.from_orm_enriched(transaction)


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
        raise NotFoundError("Account", transaction.account_id)

    asset = db.query(Asset).filter(Asset.id == transaction.asset_id).first()
    if not asset:
        raise NotFoundError("Asset", transaction.asset_id)

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
            sell_result = svc.process_sell(holding, transaction.quantity)
            if transaction.price_per_unit and transaction.quantity:
                db_transaction.realized_pnl_usd = compute_realized_pnl_usd(
                    sell_quantity=transaction.quantity,
                    sell_price_per_unit=transaction.price_per_unit,
                    sell_fees=transaction.fees or Decimal("0"),
                    total_cost_basis_sold=sell_result.total_cost_basis_sold,
                    currency_rate_to_usd=db_transaction.currency_rate_to_usd_at_date,
                )

        db.commit()
        loaded = _load_transaction_with_relations(db, db_transaction.id)
        return TransactionSchema.from_orm_enriched(loaded)

    except TransactionError as e:
        db.rollback()
        raise BadRequestError(str(e)) from e


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
        raise NotFoundError("Transaction", transaction_id)

    holding = db.query(Holding).filter(Holding.id == db_transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise NotFoundError("Transaction", transaction_id)

    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    db.commit()
    loaded = _load_transaction_with_relations(db, db_transaction.id)

    return TransactionSchema.from_orm_enriched(loaded)


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
        raise NotFoundError("Transaction", transaction_id)

    holding = db.query(Holding).filter(Holding.id == db_transaction.holding_id).first()
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not holding or holding.account_id not in allowed_account_ids:
        raise NotFoundError("Transaction", transaction_id)

    db.delete(db_transaction)
    db.commit()

    return None
