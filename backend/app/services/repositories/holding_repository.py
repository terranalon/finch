"""Holding data access layer.

Centralizes all Holding queries to eliminate duplication across import services.
The pattern of querying holdings by (account_id, asset_id) appears 12+ times
across the codebase.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import Holding

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class HoldingRepository:
    """Centralized holding data access.

    Naming conventions:
    - find_* : Query that may return None
    - get_* : Query that raises NotFoundError if missing
    - create_* : Insert new record
    - update_* : Modify existing record
    - find_or_create_* : Upsert pattern
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, holding_id: int) -> Holding | None:
        """Find holding by primary key."""
        return self._db.query(Holding).filter(Holding.id == holding_id).first()

    def find_by_account_and_asset(self, account_id: int, asset_id: int) -> Holding | None:
        """Find holding by account and asset combination.

        This is the most common query pattern across import services.
        """
        return (
            self._db.query(Holding)
            .filter(Holding.account_id == account_id, Holding.asset_id == asset_id)
            .first()
        )

    def find_by_account(self, account_id: int) -> "Sequence[Holding]":
        """Find all holdings for an account."""
        return self._db.query(Holding).filter(Holding.account_id == account_id).all()

    def find_active_by_account(self, account_id: int) -> "Sequence[Holding]":
        """Find all active holdings for an account."""
        return (
            self._db.query(Holding)
            .filter(Holding.account_id == account_id, Holding.is_active.is_(True))
            .all()
        )

    def find_or_create(
        self,
        account_id: int,
        asset_id: int,
        *,
        quantity: Decimal = Decimal("0"),
        cost_basis: Decimal = Decimal("0"),
    ) -> tuple[Holding, bool]:
        """Find existing holding or create new one.

        Returns:
            Tuple of (holding, created) where created is True if new record.
        """
        existing = self.find_by_account_and_asset(account_id, asset_id)
        if existing:
            return existing, False

        holding = Holding(
            account_id=account_id,
            asset_id=asset_id,
            quantity=quantity,
            cost_basis=cost_basis,
        )
        self._db.add(holding)
        self._db.flush()
        logger.debug(f"Created holding for account {account_id}, asset {asset_id}")
        return holding, True

    def update_quantity(
        self,
        holding: Holding,
        quantity: Decimal,
        cost_basis: Decimal | None = None,
    ) -> Holding:
        """Update holding quantity and optionally cost basis."""
        holding.quantity = quantity
        if cost_basis is not None:
            holding.cost_basis = cost_basis
        self._db.flush()
        return holding

    def mark_inactive(self, holding: Holding) -> Holding:
        """Mark a holding as inactive (position closed)."""
        holding.is_active = False
        holding.closed_at = datetime.now()
        self._db.flush()
        return holding

    def mark_active(self, holding: Holding) -> Holding:
        """Mark a holding as active again (position reopened)."""
        holding.is_active = True
        holding.closed_at = None
        self._db.flush()
        return holding
