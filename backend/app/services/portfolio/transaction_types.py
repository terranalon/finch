"""Value objects and exceptions for transaction processing."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class BuyResult:
    """Result of processing a buy transaction."""

    holding_id: int
    new_quantity: Decimal
    new_cost_basis: Decimal
    lot_id: int


@dataclass
class SellResult:
    """Result of processing a sell transaction."""

    holding_id: int
    new_quantity: Decimal
    new_cost_basis: Decimal
    total_cost_basis_sold: Decimal
    is_closed: bool


class TransactionError(Exception):
    """Base error for transaction processing."""


class InvalidTransactionTypeError(TransactionError):
    """Raised when transaction type is not valid."""


class InsufficientQuantityError(TransactionError):
    """Raised when selling more than available quantity."""


class NoOpenLotsError(TransactionError):
    """Raised when no open lots exist for FIFO allocation."""
