"""IBKR synthetic snapshot import service.

Creates synthetic transactions from current IBKR positions for instant onboarding.
These synthetic records are replaced when the user uploads full historical data.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, BrokerDataSource, Holding, Transaction
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings

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
    return {
        **stats,
        "status": "failed",
        "errors": [*stats["errors"], error],
        "end_time": datetime.now().isoformat(),
    }


def _find_or_create_holding(db: Session, account_id: int, asset_id: int) -> Holding:
    """Find an existing holding or create a new zero-quantity one."""
    holding = (
        db.query(Holding)
        .filter(
            Holding.account_id == account_id,
            Holding.asset_id == asset_id,
        )
        .first()
    )
    if holding:
        return holding

    holding = Holding(
        account_id=account_id,
        asset_id=asset_id,
        quantity=Decimal("0"),
        cost_basis=Decimal("0"),
        is_active=False,
    )
    db.add(holding)
    db.flush()
    return holding


def _build_snapshot_positions(positions_data: list[dict]) -> list[dict]:
    """Extract non-zero positions into the serializable snapshot format."""
    return [
        {
            "symbol": p["symbol"],
            "quantity": str(p["quantity"]),
            "cost_basis": str(p["cost_basis"]),
            "currency": p.get("currency", "USD"),
        }
        for p in positions_data
        if p["quantity"] != 0
    ]


class IBKRSyntheticImportService:
    """Creates synthetic transactions from current IBKR positions."""

    @staticmethod
    def import_snapshot(db: Session, account_id: int, flex_token: str, flex_query_id: str) -> dict:
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

            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash_balances"] = cash_stats

            for position in positions_data:
                quantity = position["quantity"]
                cost_basis = position["cost_basis"]

                if quantity == 0:
                    continue

                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=position["symbol"],
                    name=position["description"],
                    asset_class=position["asset_class"],
                    currency=position.get("currency", "USD"),
                    ibkr_symbol=position["original_symbol"],
                    cusip=position.get("cusip"),
                    isin=position.get("isin"),
                    conid=position.get("conid"),
                    figi=position.get("figi"),
                )
                if created:
                    stats["assets_created"] += 1

                holding = _find_or_create_holding(db, account_id, asset.id)
                price_per_unit = abs(cost_basis / quantity)

                txn = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source.id,
                    date=today,
                    type="Buy",
                    quantity=abs(quantity),
                    price_per_unit=price_per_unit,
                    amount=abs(cost_basis),
                    fees=Decimal("0"),
                    notes="Synthetic transaction from IBKR position snapshot",
                )
                db.add(txn)
                stats["positions_imported"] += 1

            source.import_stats = {
                "snapshot_positions": _build_snapshot_positions(positions_data),
                "positions_imported": stats["positions_imported"],
                "cash_balances": cash_stats,
                "assets_created": stats["assets_created"],
            }
            source.status = "completed"

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
