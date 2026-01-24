"""Transaction hash service for deduplication."""

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
