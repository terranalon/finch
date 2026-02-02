"""Shared holdings reconstruction logic for import services.

This module provides a common function for reconstructing holdings from
transactions and updating the Holding table. Used by multiple import services
(Crypto, Meitav, IBKR) to ensure consistent behavior.
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Holding, Transaction

logger = logging.getLogger(__name__)


def reconstruct_and_update_holdings(db: Session, account_id: int) -> dict:
    """Reconstruct holdings from transactions and update the Holding table.

    This replays all transactions to calculate current quantities and cost basis,
    then updates the Holding records accordingly.

    Args:
        db: Database session
        account_id: Account ID to reconstruct holdings for

    Returns:
        Statistics dictionary with keys:
        - holdings_updated: Number of holdings updated
        - holdings_activated: Holdings that went from 0 to non-zero quantity
        - holdings_deactivated: Holdings that went from non-zero to 0 quantity
        - error: Error message if reconstruction failed (optional)
    """
    from app.services.portfolio.portfolio_reconstruction_service import (
        PortfolioReconstructionService,
    )

    stats = {
        "holdings_updated": 0,
        "holdings_activated": 0,
        "holdings_deactivated": 0,
    }

    try:
        today = date.today()
        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, today, apply_ticker_changes=False
        )

        logger.info(f"Reconstructed {len(reconstructed)} holdings for account {account_id}")

        reconstructed_map = {h["asset_id"]: h for h in reconstructed}
        holdings = db.query(Holding).filter(Holding.account_id == account_id).all()

        for holding in holdings:
            recon = reconstructed_map.pop(holding.asset_id, None)

            if recon:
                old_qty = holding.quantity
                holding.quantity = recon["quantity"]
                holding.cost_basis = recon["cost_basis"]
                holding.is_active = recon["quantity"] != 0

                if old_qty == 0 and holding.quantity != 0:
                    stats["holdings_activated"] += 1
                elif old_qty != 0 and holding.quantity == 0:
                    stats["holdings_deactivated"] += 1

                stats["holdings_updated"] += 1
                logger.debug(
                    f"Updated holding {holding.asset_id}: qty={holding.quantity}, "
                    f"cost_basis={holding.cost_basis}"
                )
            else:
                # Not in reconstruction - check if it has transactions that sum to 0
                has_transactions = (
                    db.query(Transaction).filter(Transaction.holding_id == holding.id).first()
                    is not None
                )

                if has_transactions and holding.quantity != 0:
                    holding.quantity = Decimal("0")
                    holding.cost_basis = Decimal("0")
                    holding.is_active = False
                    stats["holdings_deactivated"] += 1
                    stats["holdings_updated"] += 1
                elif holding.quantity == 0:
                    holding.is_active = False

        # Log any orphaned reconstructed holdings
        for asset_id, recon in reconstructed_map.items():
            if recon["quantity"] != 0:
                logger.warning(
                    f"Found reconstructed holding without Holding record: "
                    f"asset_id={asset_id}, qty={recon['quantity']}"
                )

        logger.info(
            f"Holdings reconstruction complete: {stats['holdings_updated']} updated, "
            f"{stats['holdings_activated']} activated, {stats['holdings_deactivated']} deactivated"
        )

    except Exception as e:
        logger.exception(f"Error reconstructing holdings: {e}")
        stats["error"] = str(e)

    return stats
