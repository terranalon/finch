"""Transaction views API router - type-specific endpoints for the tabbed UI."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account, Asset, Holding, Transaction
from app.models.user import User
from app.schemas.transaction_views import (
    CashActivityResponse,
    DividendResponse,
    ForexResponse,
    TradeResponse,
)
from app.services.currency_conversion_helper import CurrencyConversionHelper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transactions", tags=["transaction-views"])


@router.get("/trades", response_model=list[TradeResponse])
async def list_trades(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TradeResponse]:
    """
    Get list of trade transactions (Buy/Sell) for user's accounts.

    Returns enriched trade data with computed totals.
    If display_currency is provided, converts price_per_unit and total to that currency.
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    query = (
        db.query(Transaction, Holding, Asset, Account)
        .join(Holding, Transaction.holding_id == Holding.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .join(Account, Holding.account_id == Account.id)
        .filter(Transaction.type.in_(["Buy", "Sell"]), Account.id.in_(allowed_account_ids))
    )

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        query = query.filter(Account.id == account_id)

    if symbol:
        query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))

    query = query.order_by(desc(Transaction.date), desc(Transaction.id))
    results = query.offset(offset).limit(limit).all()

    trades = []
    for txn, holding, asset, account in results:
        # Compute total: qty * price + fees
        qty = txn.quantity or Decimal("0")
        price = txn.price_per_unit or Decimal("0")
        fees = txn.fees or Decimal("0")
        total = (qty * price) + fees

        # Get native currency
        native_currency = asset.currency or "USD"

        # Convert to display currency if requested
        if display_currency and display_currency != native_currency:
            price = CurrencyConversionHelper.convert_value(
                db, price, native_currency, display_currency, txn.date
            )
            fees = CurrencyConversionHelper.convert_value(
                db, fees, native_currency, display_currency, txn.date
            )
            total = CurrencyConversionHelper.convert_value(
                db, total, native_currency, display_currency, txn.date
            )
            output_currency = display_currency
        else:
            output_currency = native_currency

        trades.append(
            TradeResponse(
                id=txn.id,
                date=txn.date,
                symbol=asset.symbol,
                asset_name=asset.name,
                asset_class=asset.asset_class,
                action=txn.type,
                quantity=qty,
                price_per_unit=price,
                fees=fees,
                total=total,
                currency=output_currency,
                account_name=account.name,
                notes=txn.notes,
            )
        )

    return trades


@router.get("/dividends", response_model=list[DividendResponse])
async def list_dividends(
    account_id: int | None = None,
    symbol: str | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DividendResponse]:
    """
    Get list of dividend and income transactions for user's accounts.

    Includes: Dividend, Tax, Interest (excludes Dividend Cash which is the cash-side duplicate).
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    dividend_types = ["Dividend", "Tax", "Interest"]

    query = (
        db.query(Transaction, Holding, Asset, Account)
        .join(Holding, Transaction.holding_id == Holding.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .join(Account, Holding.account_id == Account.id)
        .filter(Transaction.type.in_(dividend_types), Account.id.in_(allowed_account_ids))
    )

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        query = query.filter(Account.id == account_id)

    if symbol:
        query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))

    query = query.order_by(desc(Transaction.date), desc(Transaction.id))
    results = query.offset(offset).limit(limit).all()

    dividends = []
    for txn, holding, asset, account in results:
        dividends.append(
            DividendResponse(
                id=txn.id,
                date=txn.date,
                symbol=asset.symbol,
                asset_name=asset.name,
                type=txn.type,
                amount=txn.amount or Decimal("0"),
                currency=asset.currency,
                account_name=account.name,
                notes=txn.notes,
            )
        )

    return dividends


@router.get("/forex", response_model=list[ForexResponse])
async def list_forex(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ForexResponse]:
    """
    Get list of forex conversion transactions for user's accounts.

    Returns single record per conversion with from/to currencies and amounts.
    For legacy data (paired transactions), parses info from notes field.
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    query = (
        db.query(Transaction, Holding, Asset, Account)
        .join(Holding, Transaction.holding_id == Holding.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .join(Account, Holding.account_id == Account.id)
        .filter(Transaction.type == "Forex Conversion", Account.id.in_(allowed_account_ids))
    )

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        query = query.filter(Account.id == account_id)

    query = query.order_by(desc(Transaction.date), desc(Transaction.id))
    results = query.offset(offset).limit(limit).all()

    forex_list = []
    seen_legacy_pairs = set()  # Track legacy pairs to avoid duplicates

    for txn, holding, asset, account in results:
        # Check if this is a new-style single record (has to_holding_id)
        if txn.to_holding_id is not None:
            # New format: single record with all forex fields
            to_holding = db.query(Holding).filter(Holding.id == txn.to_holding_id).first()
            to_asset = (
                db.query(Asset).filter(Asset.id == to_holding.asset_id).first()
                if to_holding
                else None
            )

            forex_list.append(
                ForexResponse(
                    id=txn.id,
                    date=txn.date,
                    from_currency=asset.symbol,
                    from_amount=txn.amount or Decimal("0"),
                    to_currency=to_asset.symbol if to_asset else "???",
                    to_amount=txn.to_amount or Decimal("0"),
                    exchange_rate=txn.exchange_rate or Decimal("0"),
                    account_name=account.name,
                    notes=txn.notes,
                )
            )
        else:
            # Legacy format: paired transactions
            # Parse from notes: "IBKR Import - Convert 1500 ILS to 420 USD @ 0.28"
            import re

            notes = txn.notes or ""
            match = re.search(r"Convert ([\d.]+) (\w+) to ([\d.]+) (\w+) @ ([\d.]+)", notes)

            if match:
                from_amt = Decimal(match.group(1))
                from_curr = match.group(2)
                to_amt = Decimal(match.group(3))
                to_curr = match.group(4)
                rate = Decimal(match.group(5))

                # Create a unique key to avoid showing both sides of the pair
                pair_key = (txn.date, from_curr, to_curr, str(from_amt), str(to_amt))
                if pair_key in seen_legacy_pairs:
                    continue
                seen_legacy_pairs.add(pair_key)

                forex_list.append(
                    ForexResponse(
                        id=txn.id,
                        date=txn.date,
                        from_currency=from_curr,
                        from_amount=from_amt,
                        to_currency=to_curr,
                        to_amount=to_amt,
                        exchange_rate=rate,
                        account_name=account.name,
                        notes=txn.notes,
                    )
                )

    return forex_list


@router.get("/cash", response_model=list[CashActivityResponse])
async def list_cash_activity(
    account_id: int | None = None,
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CashActivityResponse]:
    """
    Get list of cash activity transactions for user's accounts.

    Includes: Deposit, Withdrawal, Fee, Transfer (excludes Trade Settlement which is shown in Trades).
    If display_currency is provided, converts amount to that currency.
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    cash_types = ["Deposit", "Withdrawal", "Fee", "Transfer"]

    query = (
        db.query(Transaction, Holding, Asset, Account)
        .join(Holding, Transaction.holding_id == Holding.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .join(Account, Holding.account_id == Account.id)
        .filter(Transaction.type.in_(cash_types), Account.id.in_(allowed_account_ids))
    )

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        query = query.filter(Account.id == account_id)

    query = query.order_by(desc(Transaction.date), desc(Transaction.id))
    results = query.offset(offset).limit(limit).all()

    cash_activity = []
    for txn, holding, asset, account in results:
        # For crypto deposits/withdrawals, calculate USD value from quantity × price
        # This is critical for TWR calculation to correctly exclude external cash flows
        if asset.asset_class == "Crypto" and txn.type in ("Deposit", "Withdrawal"):
            quantity = txn.quantity or Decimal("0")
            price = txn.price_per_unit or Decimal("0")
            amount = quantity * price  # USD value of the crypto
            native_currency = "USD"
        else:
            amount = txn.amount or Decimal("0")
            native_currency = asset.currency or asset.symbol

        needs_conversion = display_currency and display_currency != native_currency

        output_currency = display_currency if needs_conversion else native_currency
        if needs_conversion:
            amount = CurrencyConversionHelper.convert_value(
                db, amount, native_currency, display_currency, txn.date
            )

        cash_activity.append(
            CashActivityResponse(
                id=txn.id,
                date=txn.date,
                type=txn.type,
                symbol=asset.symbol if asset.asset_class != "Cash" else None,
                amount=amount,
                currency=output_currency,
                account_name=account.name,
                notes=txn.notes,
            )
        )

    return cash_activity
