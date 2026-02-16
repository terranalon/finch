"""IBKR synthetic snapshot import service.

Creates synthetic transactions from current IBKR positions for instant onboarding.
These synthetic records are replaced when the user uploads full historical data.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, BrokerDataSource, Transaction
from app.models.daily_cash_balance import DailyCashBalance
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.models import IBKRCashBalance, IBKRPosition
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings
from app.services.repositories import AssetRepository, CashBalanceRepository, HoldingRepository
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
        "cash_balances": {},
        "assets_created": 0,
        "errors": [],
    }


def _fail_stats(stats: dict, error: str) -> dict:
    """Mark stats as failed with the given error message and return them."""
    stats_copy = stats.copy()
    stats_copy["status"] = "failed"
    stats_copy["errors"] = [*stats["errors"], error]
    stats_copy["end_time"] = datetime.now().isoformat()
    return stats_copy


def _compute_cost_basis_by_currency(positions: list[IBKRPosition]) -> dict[str, Decimal]:
    """Sum abs(cost_basis) of non-zero positions, grouped by currency."""
    totals: dict[str, Decimal] = {}
    for p in positions:
        if p.quantity == 0:
            continue
        totals[p.currency] = totals.get(p.currency, Decimal("0")) + abs(p.cost_basis)
    return totals


def _build_snapshot_positions(positions_data: list[IBKRPosition]) -> list[dict]:
    """Extract non-zero positions into the serializable snapshot format."""
    return [
        {
            "symbol": p.symbol,
            "quantity": str(p.quantity),
            "cost_basis": str(p.cost_basis),
            "currency": p.currency,
        }
        for p in positions_data
        if p.quantity != 0
    ]


def _create_inflated_deposits(
    db: Session,
    account_id: int,
    source_id: int,
    cash_data: list[IBKRCashBalance],
    cost_basis_by_currency: dict[str, Decimal],
    today: date,
) -> set[str]:
    """Create inflated deposit transactions and DailyCashBalance records.

    Each deposit amount = actual cash balance + total cost basis for that currency.
    For currencies with positions but no cash entry, creates a deposit for just
    the cost basis and a zero-balance DailyCashBalance record.

    Returns the set of currencies that had cash entries (for stats tracking).
    """
    asset_repo = AssetRepository(db)
    holding_repo = HoldingRepository(db)
    cash_balance_repo = CashBalanceRepository(db)
    currencies_with_cash: set[str] = set()

    for cash in cash_data:
        if cash.balance == 0 and cash.currency not in cost_basis_by_currency:
            continue
        currencies_with_cash.add(cash.currency)

        cash_asset = asset_repo.find_by_symbol(cash.symbol)
        if not cash_asset:
            continue
        cash_holding, _ = holding_repo.find_or_create(account_id, cash_asset.id)

        position_cost = cost_basis_by_currency.get(cash.currency, Decimal("0"))
        deposit_amount = cash.balance + position_cost
        if deposit_amount == 0:
            continue

        create_or_transfer_transaction(
            db=db,
            holding_id=cash_holding.id,
            source_id=source_id,
            account_id=account_id,
            txn_date=today,
            txn_type="Deposit",
            symbol=cash.symbol,
            quantity=deposit_amount,
            amount=deposit_amount,
            fees=Decimal("0"),
            notes=f"Synthetic deposit from IBKR snapshot ({cash.currency})",
        )
        cash_balance_repo.create(
            account_id=account_id,
            balance_date=today,
            currency=cash.currency,
            balance=cash.balance,
            activity="Synthetic snapshot",
            broker_source_id=source_id,
        )

    # Gap-fill: currencies with positions but no cash entry
    for currency, cost in cost_basis_by_currency.items():
        if currency in currencies_with_cash or cost == 0:
            continue

        cash_asset, _ = IBKRImportService._find_or_create_asset(
            db,
            symbol=currency,
            name=f"{currency} Cash",
            asset_class="Cash",
            currency=currency,
        )
        cash_holding, _ = holding_repo.find_or_create(account_id, cash_asset.id)

        create_or_transfer_transaction(
            db=db,
            holding_id=cash_holding.id,
            source_id=source_id,
            account_id=account_id,
            txn_date=today,
            txn_type="Deposit",
            symbol=currency,
            quantity=cost,
            amount=cost,
            fees=Decimal("0"),
            notes=f"Synthetic deposit from IBKR snapshot ({currency})",
        )
        cash_balance_repo.create(
            account_id=account_id,
            balance_date=today,
            currency=currency,
            balance=Decimal("0"),
            activity="Synthetic snapshot",
            broker_source_id=source_id,
        )

    return currencies_with_cash


def delete_synthetic_sources(db: Session, account_id: int, broker_type: str) -> dict:
    """Delete synthetic sources and their linked transactions/cash balances.

    When a user uploads real historical data, any existing synthetic sources
    for the same account+broker should be cleaned up. This function:
    1. Finds all BrokerDataSource records with source_type="synthetic"
    2. Saves their snapshot_positions from import_stats (for later validation)
    3. Deletes linked transactions and cash balances
    4. Deletes the source records themselves

    Args:
        db: Database session
        account_id: Account to clean up synthetic sources for
        broker_type: Broker type (e.g., 'ibkr')

    Returns:
        Stats about what was deleted, plus the snapshot_positions for validation
    """
    synthetic_sources = (
        db.query(BrokerDataSource)
        .filter(
            BrokerDataSource.account_id == account_id,
            BrokerDataSource.broker_type == broker_type,
            BrokerDataSource.source_type == "synthetic",
        )
        .all()
    )

    if not synthetic_sources:
        return {"deleted_sources": 0, "deleted_transactions": 0, "snapshot_positions": []}

    total_txns_deleted = 0
    total_cash_deleted = 0
    snapshot_positions: list[dict] = []

    for source in synthetic_sources:
        # Save snapshot data for validation (last source wins -- typically only one exists)
        if source.import_stats and "snapshot_positions" in source.import_stats:
            snapshot_positions = source.import_stats["snapshot_positions"]

        # Delete linked transactions
        txns_deleted = (
            db.query(Transaction)
            .filter(Transaction.broker_source_id == source.id)
            .delete(synchronize_session=False)
        )
        total_txns_deleted += txns_deleted

        # Delete linked cash balances
        cash_deleted = (
            db.query(DailyCashBalance)
            .filter(DailyCashBalance.broker_source_id == source.id)
            .delete(synchronize_session=False)
        )
        total_cash_deleted += cash_deleted

        db.delete(source)

    return {
        "deleted_sources": len(synthetic_sources),
        "deleted_transactions": total_txns_deleted,
        "deleted_cash_balances": total_cash_deleted,
        "snapshot_positions": snapshot_positions,
    }


class IBKRSyntheticImportService:
    """Creates synthetic transactions from current IBKR positions."""

    @staticmethod
    def import_snapshot(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
        pre_fetched_root: ET.Element | None = None,
    ) -> dict:
        """Fetch current positions from IBKR and create synthetic transactions.

        This creates:
        1. A BrokerDataSource with source_type='synthetic'
        2. One synthetic 'Buy' transaction per position (quantity + cost_basis)
        3. Cash balance holdings from current cash report

        The snapshot_positions are stored in import_stats for later validation
        when the user uploads real historical data.

        Returns:
            Statistics dictionary
        """
        stats = _build_initial_stats(account_id)

        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return _fail_stats(stats, f"Account {account_id} not found")

            if pre_fetched_root is not None:
                root = pre_fetched_root
            else:
                xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)
                if not xml_data:
                    return _fail_stats(
                        stats, "Failed to fetch Flex Query report. Check your token and query ID."
                    )
                root = IBKRParser.parse_xml(xml_data)
                if root is None:
                    return _fail_stats(stats, "Failed to parse Flex Query XML response")

            positions_data = IBKRParser.extract_positions(root)
            cash_data = IBKRParser.extract_cash_balances(root)
            today = date.today()

            source = BrokerDataSource(
                account_id=account_id,
                broker_type="ibkr",
                source_type="synthetic",
                source_identifier=f"Synthetic Snapshot {today.isoformat()}",
                start_date=today,
                end_date=today,
                status="pending",
            )
            db.add(source)
            db.flush()

            cost_basis_by_currency = _compute_cost_basis_by_currency(positions_data)

            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash_balances"] = cash_stats

            _create_inflated_deposits(
                db, account_id, source.id, cash_data, cost_basis_by_currency, today
            )

            asset_repo = AssetRepository(db)
            holding_repo = HoldingRepository(db)

            for position in positions_data:
                quantity = position.quantity
                cost_basis = position.cost_basis

                if quantity == 0:
                    continue

                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=position.symbol,
                    name=position.description,
                    asset_class=position.asset_class,
                    currency=position.currency,
                    ibkr_symbol=position.original_symbol,
                    cusip=position.cusip,
                    isin=position.isin,
                    conid=position.conid,
                    figi=position.figi,
                )
                if created:
                    stats["assets_created"] += 1

                holding, _ = holding_repo.find_or_create(account_id, asset.id)
                price_per_unit = abs(cost_basis / quantity)

                result, txn = create_or_transfer_transaction(
                    db=db,
                    holding_id=holding.id,
                    source_id=source.id,
                    account_id=account_id,
                    txn_date=today,
                    txn_type="Buy",
                    symbol=position.symbol,
                    quantity=abs(quantity),
                    price=price_per_unit,
                    amount=abs(cost_basis),
                    fees=Decimal("0"),
                    notes="Synthetic transaction from IBKR position snapshot",
                )
                if result in (DedupResult.NEW, DedupResult.TRANSFERRED):
                    stats["positions_imported"] += 1

                # Trade Settlement: record cash impact (matches import_service.py pattern)
                cash_asset = asset_repo.find_by_symbol(position.currency)
                if cash_asset:
                    cash_holding, _ = holding_repo.find_or_create(account_id, cash_asset.id)
                    db.add(
                        Transaction(
                            holding_id=cash_holding.id,
                            broker_source_id=source.id,
                            date=today,
                            type="Trade Settlement",
                            amount=-abs(cost_basis),
                            notes=f"Cash settlement for {position.symbol} synthetic buy",
                        )
                    )

            source.import_stats = {
                "snapshot_positions": _build_snapshot_positions(positions_data),
                "positions_imported": stats["positions_imported"],
                "cash_balances": cash_stats,
                "assets_created": stats["assets_created"],
            }
            source.status = "completed"

            db.flush()  # ensure all transactions are visible to reconstruction
            reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
            stats["holdings_reconstruction"] = reconstruction_stats

            db.commit()
            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            return stats

        except Exception as e:
            db.rollback()
            logger.error("Synthetic snapshot import failed: %s", e, exc_info=True)
            return _fail_stats(stats, str(e))
