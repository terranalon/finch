"""KuCoin synthetic snapshot import service.

Creates synthetic transactions from current KuCoin balances for instant onboarding.
These synthetic records are replaced when the user uploads full historical CSV data.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, BrokerDataSource
from app.services.brokers.kucoin.client import KuCoinAPIError, KuCoinClient
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings
from app.services.shared.transaction_hash_service import (
    DedupResult,
    create_or_transfer_transaction,
)

logger = logging.getLogger(__name__)


def _build_initial_stats(account_id: int) -> dict:
    """Build the initial statistics dictionary for a snapshot import."""
    return {
        "account_id": account_id,
        "start_time": datetime.now().isoformat(),
        "source_type": "synthetic",
        "status": "in_progress",
        "positions_imported": 0,
        "assets_created": 0,
        "errors": [],
    }


def _fail_stats(stats: dict, error: str) -> dict:
    """Mark stats as failed with the given error message and return them."""
    return {
        **stats,
        "status": "failed",
        "errors": [*stats["errors"], error],
        "end_time": datetime.now().isoformat(),
    }


class KuCoinSyntheticImportService:
    """Creates synthetic transactions from current KuCoin balances."""

    @staticmethod
    def import_snapshot(
        db: Session,
        account_id: int,
        client: KuCoinClient,
        balances: dict[str, Decimal] | None = None,
    ) -> dict:
        """Fetch current balances and create synthetic Buy transactions.

        Creates:
        1. A BrokerDataSource with source_type='synthetic'
        2. One synthetic 'Buy' transaction per non-zero balance
        3. Stores snapshot_positions in import_stats for later validation

        Args:
            balances: Pre-fetched balances from the orchestrator. If None,
                      balances are fetched from the API. Pass pre-fetched
                      balances to avoid a duplicate API call.

        Returns:
            Statistics dictionary
        """
        stats = _build_initial_stats(account_id)

        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return _fail_stats(stats, f"Account {account_id} not found")

            if balances is None:
                balances = client.get_account_balances()
            today = date.today()

            source = BrokerDataSource(
                account_id=account_id,
                broker_type="kucoin",
                source_type="synthetic",
                source_identifier=f"Synthetic Snapshot {today.isoformat()}",
                start_date=today,
                end_date=today,
                status="pending",
            )
            db.add(source)
            db.flush()

            snapshot_positions: list[dict] = []

            # Lazy import to avoid circular imports via kucoin/__init__.py
            from app.services.brokers.shared.crypto_import_service import CryptoImportService

            crypto_service = CryptoImportService(db, "kucoin")

            for currency, quantity in balances.items():
                if quantity == Decimal("0"):
                    continue

                holding, asset_created = crypto_service.get_or_create_holding(
                    account_id, currency, "Crypto", currency
                )
                if asset_created:
                    stats["assets_created"] += 1

                result, _ = create_or_transfer_transaction(
                    db=db,
                    holding_id=holding.id,
                    source_id=source.id,
                    account_id=account_id,
                    txn_date=today,
                    txn_type="Buy",
                    symbol=currency,
                    quantity=quantity,
                    amount=Decimal("0"),  # No cost basis available from KuCoin API
                    fees=Decimal("0"),
                    notes="Synthetic transaction from KuCoin position snapshot",
                )
                if result in (DedupResult.NEW, DedupResult.TRANSFERRED):
                    stats["positions_imported"] += 1

                snapshot_positions.append(
                    {
                        "symbol": currency,
                        "quantity": str(quantity),
                    }
                )

            source.import_stats = {
                "snapshot_positions": snapshot_positions,
                "positions_imported": stats["positions_imported"],
                "assets_created": stats["assets_created"],
            }
            source.status = "completed"

            db.flush()
            reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
            stats["holdings_reconstruction"] = reconstruction_stats

            db.commit()
            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            stats["snapshot_positions"] = snapshot_positions
            return stats

        except KuCoinAPIError as e:
            db.rollback()
            logger.error("KuCoin snapshot import API error: %s", e)
            return _fail_stats(stats, str(e))
        except Exception as e:
            db.rollback()
            logger.error("KuCoin snapshot import failed: %s", e, exc_info=True)
            return _fail_stats(stats, str(e))
