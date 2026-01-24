"""Transaction hash service for deduplication.

This module provides the canonical way to create transactions during broker imports.
All import services should use `create_or_transfer_transaction()` to ensure:
1. Consistent hash-based deduplication
2. Latest-wins ownership transfer for overlapping imports
3. Proper tracking of external transaction IDs

Example usage in an import service:
    result, txn = create_or_transfer_transaction(
        db=self.db,
        holding_id=holding.id,
        source_id=source_id,
        txn_date=parsed_txn.trade_date,
        txn_type=parsed_txn.transaction_type,
        symbol=parsed_txn.symbol,
        quantity=parsed_txn.quantity,
        price=parsed_txn.price_per_unit,
        fees=parsed_txn.fees,
        amount=parsed_txn.amount,
        external_txn_id=parsed_txn.external_transaction_id,
        notes=f"Import - {parsed_txn.notes}",
    )
    if result == DedupResult.NEW:
        stats["imported"] += 1
    elif result == DedupResult.TRANSFERRED:
        stats["transferred"] += 1
    else:
        stats["skipped"] += 1
"""

import hashlib
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Transaction


class DedupResult(Enum):
    """Result of transaction deduplication check."""

    NEW = "new"  # No existing transaction, create new
    TRANSFERRED = "transferred"  # Ownership transferred to new source
    SKIPPED = "skipped"  # Already owned by this source

    def update_stats(self, stats: dict) -> None:
        """Update import statistics based on this result.

        Args:
            stats: Dictionary with 'imported', 'transferred', 'skipped' keys
        """
        if self == DedupResult.NEW:
            stats["imported"] += 1
        elif self == DedupResult.TRANSFERRED:
            stats["transferred"] += 1
        else:
            stats["skipped"] += 1


def check_and_transfer_ownership(
    db: "Session",
    content_hash: str,
    source_id: int | None,
) -> tuple[DedupResult, "Transaction | None"]:
    """Check for existing transaction by hash and handle ownership transfer.

    Implements the latest-wins policy: if a transaction exists under a different
    source, ownership is transferred to the new source.

    Args:
        db: Database session
        content_hash: SHA256 hash of transaction content
        source_id: New broker source ID

    Returns:
        Tuple of (DedupResult, existing_transaction or None)
    """
    from app.models import Transaction

    existing = db.query(Transaction).filter(Transaction.content_hash == content_hash).first()

    if not existing:
        return DedupResult.NEW, None

    if existing.broker_source_id != source_id:
        existing.broker_source_id = source_id
        return DedupResult.TRANSFERRED, existing

    return DedupResult.SKIPPED, existing


def create_or_transfer_transaction(
    db: "Session",
    holding_id: int,
    source_id: int | None,
    txn_date: date,
    txn_type: str,
    symbol: str,
    quantity: Decimal | None = None,
    price: Decimal | None = None,
    fees: Decimal | None = None,
    amount: Decimal | None = None,
    external_txn_id: str | None = None,
    notes: str | None = None,
    # Additional fields for special transaction types
    to_holding_id: int | None = None,
    to_amount: Decimal | None = None,
    exchange_rate: Decimal | None = None,
) -> tuple[DedupResult, "Transaction"]:
    """Create a transaction with automatic hash-based deduplication.

    This is the canonical way to create transactions during broker imports.
    It handles:
    1. Computing the content hash from transaction fields
    2. Checking for existing transactions with the same hash
    3. Transferring ownership if duplicate exists under different source
    4. Creating a new transaction if no duplicate exists

    Args:
        db: Database session
        holding_id: ID of the holding this transaction belongs to
        source_id: Broker data source ID for tracking import lineage
        txn_date: Transaction date
        txn_type: Transaction type (Buy, Sell, Dividend, Deposit, etc.)
        symbol: Asset symbol (used for hash computation)
        quantity: Transaction quantity (for Buy/Sell)
        price: Price per unit (for Buy/Sell)
        fees: Transaction fees
        amount: Transaction amount (for dividends, deposits, etc.)
        external_txn_id: Broker's unique transaction ID
        notes: Transaction notes
        to_holding_id: Target holding ID (for Forex Conversion)
        to_amount: Target amount (for Forex Conversion)
        exchange_rate: Exchange rate (for Forex Conversion)

    Returns:
        Tuple of (DedupResult, Transaction)
        - DedupResult.NEW: New transaction was created
        - DedupResult.TRANSFERRED: Existing transaction ownership transferred
        - DedupResult.SKIPPED: Already owned by this source (no change)
    """
    from app.models import Transaction

    # Normalize fees for hash computation
    fees_normalized = fees or Decimal("0")

    # For transactions without quantity (dividends, deposits), use amount
    quantity_for_hash = quantity if quantity is not None else (amount or Decimal("0"))

    # Compute content hash
    content_hash = compute_transaction_hash(
        external_txn_id=external_txn_id,
        txn_date=txn_date,
        symbol=symbol,
        txn_type=txn_type,
        quantity=quantity_for_hash,
        price=price,
        fees=fees_normalized,
    )

    # Check for existing transaction and handle ownership transfer
    dedup_result, existing = check_and_transfer_ownership(db, content_hash, source_id)

    if dedup_result != DedupResult.NEW:
        return dedup_result, existing

    # Create new transaction
    txn = Transaction(
        holding_id=holding_id,
        broker_source_id=source_id,
        date=txn_date,
        type=txn_type,
        quantity=quantity,
        price_per_unit=price,
        fees=fees_normalized,
        amount=amount,
        notes=notes,
        external_transaction_id=external_txn_id,
        content_hash=content_hash,
        # Optional fields for special transaction types
        to_holding_id=to_holding_id,
        to_amount=to_amount,
        exchange_rate=exchange_rate,
    )
    db.add(txn)

    return DedupResult.NEW, txn


def compute_transaction_hash(
    external_txn_id: str | None,
    txn_date: date,
    symbol: str,
    txn_type: str,
    quantity: Decimal,
    price: Decimal | None,
    fees: Decimal,
) -> str:
    """Compute SHA256 hash of transaction identifying fields.

    The hash includes the broker's external transaction ID when available,
    making it unique even for otherwise identical transactions.

    Args:
        external_txn_id: Broker's transaction ID (e.g., Kraken refid, IBKR tradeID)
        txn_date: Transaction date
        symbol: Asset symbol
        txn_type: Transaction type (Buy, Sell, Dividend, etc.)
        quantity: Transaction quantity (normalized to 8 decimals)
        price: Price per unit (normalized, or None)
        fees: Transaction fees

    Returns:
        64-character SHA256 hex digest
    """
    # Normalize values for consistent hashing
    components = [
        external_txn_id or "",
        txn_date.isoformat(),
        symbol.upper(),
        txn_type,
        f"{quantity:.8f}",
        f"{price:.8f}" if price is not None else "null",
        f"{fees:.8f}",
    ]

    content = "|".join(components)
    return hashlib.sha256(content.encode()).hexdigest()
