"""Service for detecting and handling corporate actions (symbol changes, splits, etc.)"""

import logging
from datetime import date
from decimal import Decimal

import yfinance as yf
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import Asset, CorporateAction, Holding, Transaction

logger = logging.getLogger(__name__)


class CorporateActionsService:
    """
    Service for detecting and managing corporate actions.

    Automatically detects:
    - Symbol changes (ticker rebranding)
    - Potential mergers (based on transaction patterns)
    - Delisted stocks with orphaned positions
    """

    @staticmethod
    def detect_symbol_changes(db: Session, account_id: int) -> list[dict]:
        """
        Detect potential symbol changes by finding:
        1. Assets with final positive quantities in transactions (bought but not sold)
        2. No matching position in current IBKR holdings
        3. Last transaction was > 30 days ago (not recently traded)
        4. yfinance shows stock is delisted/no data

        Returns list of potential symbol changes for manual review.
        """
        logger.info(f"Detecting potential symbol changes for account {account_id}")

        # Get all assets that had transactions
        assets_with_txns = (
            db.query(Asset)
            .join(Holding, Asset.id == Holding.asset_id)
            .join(Transaction, Holding.id == Transaction.holding_id)
            .filter(
                Holding.account_id == account_id,
                Asset.asset_class == "Stock",  # Only stocks can have symbol changes
            )
            .distinct()
            .all()
        )

        potential_changes = []

        for asset in assets_with_txns:
            # Calculate net position from transactions
            transactions = (
                db.query(Transaction)
                .join(Holding)
                .filter(
                    Holding.asset_id == asset.id,
                    Holding.account_id == account_id,
                    Transaction.type.in_(["Buy", "Sell"]),
                )
                .order_by(Transaction.date)
                .all()
            )

            if not transactions:
                continue

            # Calculate running total
            net_quantity = Decimal("0")
            last_txn_date = None

            for txn in transactions:
                if txn.type == "Buy":
                    net_quantity += txn.quantity
                elif txn.type == "Sell":
                    net_quantity -= txn.quantity
                last_txn_date = txn.date

            # Check if this looks like an orphaned position
            if net_quantity > 0 and last_txn_date:
                # Check if last transaction was > 30 days ago
                days_since_last_txn = (date.today() - last_txn_date).days

                if days_since_last_txn > 30:
                    # Check if symbol is still trading using yfinance
                    is_delisted = CorporateActionsService._check_if_delisted(asset.symbol)

                    if is_delisted:
                        potential_changes.append(
                            {
                                "asset_id": asset.id,
                                "symbol": asset.symbol,
                                "name": asset.name,
                                "orphaned_quantity": float(net_quantity),
                                "last_transaction_date": last_txn_date.isoformat(),
                                "days_since_last_transaction": days_since_last_txn,
                                "status": "delisted_or_renamed",
                            }
                        )

        logger.info(f"Found {len(potential_changes)} potential symbol changes")
        return potential_changes

    @staticmethod
    def _check_if_delisted(symbol: str) -> bool:
        """
        Check if a symbol appears to be delisted using yfinance.

        Returns:
            True if delisted/no data, False if actively trading
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")

            # If no data in last month, likely delisted
            if hist.empty:
                logger.debug(f"{symbol}: No trading data found (likely delisted)")
                return True

            # Check if last data point is recent (within 7 days)
            if not hist.index.empty:
                last_date = hist.index[-1].date()
                days_since_data = (date.today() - last_date).days

                if days_since_data > 7:
                    logger.debug(
                        f"{symbol}: Last data {days_since_data} days old (possibly delisted)"
                    )
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking {symbol}: {e}")
            # If we can't check, assume it might be delisted
            return True

    @staticmethod
    def record_symbol_change(
        db: Session,
        old_symbol: str,
        new_symbol: str,
        effective_date: date,
        notes: str | None = None,
    ) -> CorporateAction:
        """
        Manually record a symbol change.

        Args:
            db: Database session
            old_symbol: Previous ticker symbol (e.g., "CEP")
            new_symbol: New ticker symbol (e.g., "XXI")
            effective_date: Date when symbol changed
            notes: Optional notes about the change

        Returns:
            Created CorporateAction record
        """
        # Get assets
        old_asset = db.query(Asset).filter(Asset.symbol == old_symbol).first()
        new_asset = db.query(Asset).filter(Asset.symbol == new_symbol).first()

        if not old_asset:
            raise ValueError(f"Asset with symbol '{old_symbol}' not found")
        if not new_asset:
            raise ValueError(f"Asset with symbol '{new_symbol}' not found")

        # Check if already exists
        existing = (
            db.query(CorporateAction)
            .filter(
                and_(
                    CorporateAction.old_asset_id == old_asset.id,
                    CorporateAction.new_asset_id == new_asset.id,
                    CorporateAction.action_type == "SYMBOL_CHANGE",
                )
            )
            .first()
        )

        if existing:
            logger.info(f"Symbol change {old_symbol} -> {new_symbol} already recorded")
            return existing

        # Create new record
        action = CorporateAction(
            action_type="SYMBOL_CHANGE",
            old_asset_id=old_asset.id,
            new_asset_id=new_asset.id,
            effective_date=effective_date,
            ratio=Decimal("1.0"),  # 1:1 for symbol changes
            notes=notes or f"{old_asset.name} changed ticker to {new_symbol}",
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        logger.info(f"Recorded symbol change: {old_symbol} -> {new_symbol} on {effective_date}")
        return action

    @staticmethod
    def get_symbol_successor(db: Session, asset_id: int) -> tuple[int, str] | None:
        """
        Get the successor asset if this symbol was changed.

        Args:
            asset_id: Asset ID to check

        Returns:
            Tuple of (new_asset_id, new_symbol) if symbol changed, None otherwise
        """
        action = (
            db.query(CorporateAction)
            .filter(
                and_(
                    CorporateAction.old_asset_id == asset_id,
                    CorporateAction.action_type == "SYMBOL_CHANGE",
                )
            )
            .first()
        )

        if action and action.new_asset:
            return (action.new_asset_id, action.new_asset.symbol)

        return None

    @staticmethod
    def apply_corporate_actions_to_reconstruction(
        db: Session, reconstructed_holdings: list[dict]
    ) -> list[dict]:
        """
        Apply known corporate actions to reconstruction results.

        Merges holdings that had symbol changes:
        - CEP (96 shares) + XXI (100 shares) = XXI (196 shares)

        Args:
            db: Database session
            reconstructed_holdings: Holdings from reconstruction service

        Returns:
            Modified holdings list with corporate actions applied
        """
        # Build map of old_asset_id -> new_asset_id
        symbol_changes = (
            db.query(CorporateAction).filter(CorporateAction.action_type == "SYMBOL_CHANGE").all()
        )

        # Map: old_asset_id -> (new_asset_id, new_symbol, effective_date)
        successor_map = {}
        for action in symbol_changes:
            if action.new_asset_id:
                successor_map[action.old_asset_id] = (
                    action.new_asset_id,
                    action.new_asset.symbol,
                    action.effective_date,
                )

        # Apply changes: merge old symbols into new ones
        merged_holdings = {}

        for holding in reconstructed_holdings:
            asset_id = holding["asset_id"]
            symbol = holding["symbol"]
            quantity = holding["quantity"]
            cost_basis = holding["cost_basis"]

            # Check if this asset has a successor
            if asset_id in successor_map:
                new_asset_id, new_symbol, _ = successor_map[asset_id]
                logger.debug(f"Merging {symbol} ({quantity} shares) into {new_symbol}")

                # Merge into successor
                if new_asset_id in merged_holdings:
                    merged_holdings[new_asset_id]["quantity"] += quantity
                    merged_holdings[new_asset_id]["cost_basis"] += cost_basis
                else:
                    merged_holdings[new_asset_id] = {
                        **holding,
                        "asset_id": new_asset_id,
                        "symbol": new_symbol,
                        "quantity": quantity,
                        "cost_basis": cost_basis,
                        "merged_from": [symbol],
                    }
            else:
                # No successor, keep as is
                if asset_id in merged_holdings:
                    # Shouldn't happen, but merge if needed
                    merged_holdings[asset_id]["quantity"] += quantity
                    merged_holdings[asset_id]["cost_basis"] += cost_basis
                else:
                    merged_holdings[asset_id] = holding

        return list(merged_holdings.values())
