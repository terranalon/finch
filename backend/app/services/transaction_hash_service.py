"""Transaction hash service for deduplication."""

import hashlib
from datetime import date
from decimal import Decimal


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
