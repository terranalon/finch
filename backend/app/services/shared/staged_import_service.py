"""Staged import service for non-blocking IBKR imports.

This service wraps the existing import logic to use staging tables,
keeping the UI responsive during long-running imports.

Architecture:
1. Create staging tables (same structure as production)
2. Copy production data to staging (enables duplicate detection)
3. Run existing import logic against staging tables
4. Merge staging → production in a quick atomic operation
5. Clean up staging tables

The import logic is 100% unchanged - only the target tables differ.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Account
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.shared.staging_utils import (
    cleanup_staging,
    copy_production_to_staging,
    create_staging_tables,
    merge_staging_to_production,
)

logger = logging.getLogger(__name__)


class StagedImportService:
    """Service for non-blocking imports using staging tables."""

    @staticmethod
    def import_with_staging(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
    ) -> dict[str, Any]:
        """
        Import IBKR data using staging tables for UI responsiveness.

        This method provides the same result as IBKRFlexImportService.import_all()
        but uses staging tables to minimize lock time on production tables.

        The import logic is identical - only the commit strategy differs:
        - Traditional: One long transaction (5+ minutes of locks)
        - Staged: Import to staging, then quick merge (~1 second of locks)

        Args:
            db: Database session
            account_id: Account ID to import into
            flex_token: IBKR Flex Web Service token
            flex_query_id: Flex Query ID

        Returns:
            Statistics dictionary (same format as IBKRFlexImportService)
        """
        logger.info(f"Starting staged IBKR import for account {account_id}")

        stats = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "import_method": "staged",
            "positions": {},
            "transactions": {},
            "dividends": {},
            "transfers": {},
            "forex": {},
            "cash": {},
            "staging": {},
            "merge": {},
            "errors": [],
            "warnings": [],
        }

        try:
            # Validate account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                stats["status"] = "failed"
                stats["errors"].append(f"Account {account_id} not found")
                return stats

            # Phase 1: Setup staging environment
            logger.info("Phase 1: Setting up staging tables...")
            create_staging_tables(db)
            copy_stats = copy_production_to_staging(db, account_id)
            stats["staging"]["setup"] = copy_stats

            # Phase 2: Fetch and parse IBKR data (no DB writes yet)
            logger.info("Phase 2: Fetching IBKR Flex Query report...")
            xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)

            if not xml_data:
                stats["status"] = "failed"
                stats["errors"].append("Failed to fetch Flex Query report")
                cleanup_staging(db)
                return stats

            logger.info(f"Fetched {len(xml_data)} bytes of data")

            # Parse XML
            root = IBKRParser.parse_xml(xml_data)
            if root is None:
                stats["status"] = "failed"
                stats["errors"].append("Failed to parse XML response")
                cleanup_staging(db)
                return stats

            # Extract all data sections
            positions_data = IBKRParser.extract_positions(root)
            transactions_data = IBKRParser.extract_transactions(root)
            dividends_data = IBKRParser.extract_dividends(root)
            transfers_data = IBKRParser.extract_transfers(root)
            forex_data = IBKRParser.extract_forex_transactions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            logger.info(
                f"Extracted {len(positions_data)} positions, "
                f"{len(transactions_data)} transactions, "
                f"{len(dividends_data)} dividends"
            )

            # Phase 3: Import to staging tables
            logger.info("Phase 3: Importing to staging tables...")
            import_stats = StagedImportService._import_to_staging(
                db,
                account_id,
                positions_data,
                transactions_data,
                dividends_data,
                transfers_data,
                forex_data,
                cash_data,
            )

            stats["positions"] = import_stats.get("positions", {})
            stats["transactions"] = import_stats.get("transactions", {})
            stats["dividends"] = import_stats.get("dividends", {})
            stats["transfers"] = import_stats.get("transfers", {})
            stats["forex"] = import_stats.get("forex", {})
            stats["cash"] = import_stats.get("cash", {})

            # Phase 4: Quick merge from staging to production
            logger.info("Phase 4: Merging staging to production (quick operation)...")
            merge_stats = merge_staging_to_production(db, account_id)
            stats["merge"] = merge_stats

            # Phase 5: Cleanup
            logger.info("Phase 5: Cleaning up staging tables...")
            cleanup_staging(db)

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()

            logger.info(
                f"Staged import completed: "
                f"{merge_stats.get('assets_inserted', 0)} new assets, "
                f"{merge_stats.get('holdings_inserted', 0)} new holdings, "
                f"{merge_stats.get('transactions_inserted', 0)} new transactions"
            )

            return stats

        except Exception as e:
            logger.exception(f"Staged import failed: {str(e)}")
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()

            # Try to cleanup staging on failure
            try:
                cleanup_staging(db)
            except Exception:
                logger.warning("Failed to cleanup staging tables")

            return stats

    @staticmethod
    def _import_to_staging(
        db: Session,
        account_id: int,
        positions_data: list[dict],
        transactions_data: list[dict],
        dividends_data: list[dict],
        transfers_data: list[dict],
        forex_data: list[dict],
        cash_data: list[dict],
    ) -> dict[str, Any]:
        """
        Import data to staging tables using direct SQL.

        This method replicates the logic of IBKRImportService but writes
        to staging tables directly, avoiding ORM model bindings.
        """
        stats = {
            "positions": {"total": len(positions_data), "imported": 0, "errors": []},
            "transactions": {"total": len(transactions_data), "imported": 0, "errors": []},
            "dividends": {"total": len(dividends_data), "imported": 0, "errors": []},
            "transfers": {"total": len(transfers_data), "imported": 0, "errors": []},
            "forex": {"total": len(forex_data), "imported": 0, "errors": []},
            "cash": {"total": len(cash_data), "imported": 0, "errors": []},
        }

        # Import positions
        for pos in positions_data:
            try:
                StagedImportService._import_position_to_staging(db, account_id, pos)
                stats["positions"]["imported"] += 1
            except Exception as e:
                stats["positions"]["errors"].append(f"{pos.get('symbol')}: {str(e)}")

        # Import cash balances
        for cash in cash_data:
            try:
                StagedImportService._import_cash_to_staging(db, account_id, cash)
                stats["cash"]["imported"] += 1
            except Exception as e:
                stats["cash"]["errors"].append(f"{cash.get('symbol')}: {str(e)}")

        # Import transactions
        for txn in transactions_data:
            try:
                StagedImportService._import_transaction_to_staging(db, account_id, txn)
                stats["transactions"]["imported"] += 1
            except Exception as e:
                stats["transactions"]["errors"].append(f"{txn.get('symbol')}: {str(e)}")

        # Import dividends
        for div in dividends_data:
            try:
                StagedImportService._import_dividend_to_staging(db, account_id, div)
                stats["dividends"]["imported"] += 1
            except Exception as e:
                stats["dividends"]["errors"].append(f"{div.get('symbol')}: {str(e)}")

        # Import transfers
        for transfer in transfers_data:
            try:
                StagedImportService._import_transfer_to_staging(db, account_id, transfer)
                stats["transfers"]["imported"] += 1
            except Exception as e:
                stats["transfers"]["errors"].append(f"{transfer.get('type')}: {str(e)}")

        # Import forex
        for forex in forex_data:
            try:
                StagedImportService._import_forex_to_staging(db, account_id, forex)
                stats["forex"]["imported"] += 1
            except Exception as e:
                stats["forex"]["errors"].append(
                    f"{forex.get('from_currency')}->{forex.get('to_currency')}: {str(e)}"
                )

        db.commit()
        return stats

    @staticmethod
    def _find_or_create_staging_asset(db: Session, pos: dict) -> int:
        """Find or create an asset in staging tables. Returns staging asset ID."""
        symbol = pos["symbol"]

        # Check if asset exists in staging
        result = db.execute(
            text("SELECT id FROM staging.assets WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
        row = result.fetchone()
        if row:
            return row[0]

        # Create new asset in staging
        result = db.execute(
            text("""
                INSERT INTO staging.assets (
                    symbol, name, asset_class, currency, data_source,
                    cusip, isin, conid, figi, is_manual_valuation
                ) VALUES (
                    :symbol, :name, :asset_class, :currency, 'IBKR',
                    :cusip, :isin, :conid, :figi, false
                )
                RETURNING id
            """),
            {
                "symbol": symbol,
                "name": pos.get("description", symbol),
                "asset_class": pos.get("asset_class", "Stock"),
                "currency": pos.get("currency", "USD"),
                "cusip": pos.get("cusip"),
                "isin": pos.get("isin"),
                "conid": pos.get("conid"),
                "figi": pos.get("figi"),
            },
        )
        return result.fetchone()[0]

    @staticmethod
    def _find_or_create_staging_holding(db: Session, account_id: int, staging_asset_id: int) -> int:
        """Find or create a holding in staging tables. Returns staging holding ID."""
        # Check if holding exists
        result = db.execute(
            text("""
                SELECT id FROM staging.holdings
                WHERE account_id = :account_id AND staging_asset_id = :staging_asset_id
            """),
            {"account_id": account_id, "staging_asset_id": staging_asset_id},
        )
        row = result.fetchone()
        if row:
            return row[0]

        # Get asset_id from staging asset (for FK reference)
        result = db.execute(
            text("SELECT COALESCE(original_id, id) FROM staging.assets WHERE id = :id"),
            {"id": staging_asset_id},
        )
        asset_id = result.fetchone()[0]

        # Create new holding
        result = db.execute(
            text("""
                INSERT INTO staging.holdings (
                    account_id, asset_id, staging_asset_id, quantity, cost_basis, is_active
                ) VALUES (
                    :account_id, :asset_id, :staging_asset_id, 0, 0, true
                )
                RETURNING id
            """),
            {
                "account_id": account_id,
                "asset_id": asset_id,
                "staging_asset_id": staging_asset_id,
            },
        )
        return result.fetchone()[0]

    @staticmethod
    def _import_position_to_staging(db: Session, account_id: int, pos: dict) -> None:
        """Import a single position to staging tables."""
        # Skip forex pair positions
        symbol = pos["symbol"]
        currency_codes = {"USD", "CAD", "ILS", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD"}
        if "." in symbol:
            parts = symbol.split(".")
            if len(parts) == 2 and parts[0] in currency_codes and parts[1] in currency_codes:
                return

        staging_asset_id = StagedImportService._find_or_create_staging_asset(db, pos)
        staging_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, staging_asset_id
        )

        # Update holding quantity and cost_basis
        db.execute(
            text("""
                UPDATE staging.holdings
                SET quantity = :quantity, cost_basis = :cost_basis, is_active = :is_active
                WHERE id = :id
            """),
            {
                "id": staging_holding_id,
                "quantity": pos["quantity"],
                "cost_basis": pos["cost_basis"],
                "is_active": pos["quantity"] != 0,
            },
        )

    @staticmethod
    def _import_cash_to_staging(db: Session, account_id: int, cash: dict) -> None:
        """Import a cash balance to staging tables."""
        symbol = cash["symbol"]
        currency = cash["currency"]
        balance = cash["balance"]

        # Find or create cash asset
        result = db.execute(
            text("SELECT id FROM staging.assets WHERE symbol = :symbol"),
            {"symbol": symbol},
        )
        row = result.fetchone()

        if row:
            staging_asset_id = row[0]
        else:
            result = db.execute(
                text("""
                    INSERT INTO staging.assets (
                        symbol, name, asset_class, currency, data_source,
                        last_fetched_price, is_manual_valuation
                    ) VALUES (
                        :symbol, :name, 'Cash', :currency, 'IBKR', 1, false
                    )
                    RETURNING id
                """),
                {
                    "symbol": symbol,
                    "name": cash.get("description", f"{currency} Cash"),
                    "currency": currency,
                },
            )
            staging_asset_id = result.fetchone()[0]

        # Find or create holding
        staging_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, staging_asset_id
        )

        # Update balance
        db.execute(
            text("""
                UPDATE staging.holdings
                SET quantity = :balance, cost_basis = :balance, is_active = :is_active
                WHERE id = :id
            """),
            {
                "id": staging_holding_id,
                "balance": balance,
                "is_active": balance != 0,
            },
        )

    @staticmethod
    def _import_transaction_to_staging(db: Session, account_id: int, txn: dict) -> None:
        """Import a transaction to staging tables."""
        # Skip forex pair transactions
        symbol = txn["symbol"]
        currency_codes = {"USD", "CAD", "ILS", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD"}
        if "." in symbol:
            parts = symbol.split(".")
            if len(parts) == 2 and parts[0] in currency_codes and parts[1] in currency_codes:
                return

        staging_asset_id = StagedImportService._find_or_create_staging_asset(db, txn)
        staging_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, staging_asset_id
        )

        # Check for duplicate
        result = db.execute(
            text("""
                SELECT id FROM staging.transactions
                WHERE staging_holding_id = :holding_id
                AND date = :date
                AND type = :type
                AND quantity = :quantity
            """),
            {
                "holding_id": staging_holding_id,
                "date": txn["trade_date"],
                "type": txn["transaction_type"],
                "quantity": txn["quantity"],
            },
        )
        if result.fetchone():
            return  # Duplicate, skip

        # Insert transaction
        db.execute(
            text("""
                INSERT INTO staging.transactions (
                    staging_holding_id, holding_id, date, type, quantity,
                    price_per_unit, fees, notes
                ) VALUES (
                    :staging_holding_id, :holding_id, :date, :type, :quantity,
                    :price, :fees, :notes
                )
            """),
            {
                "staging_holding_id": staging_holding_id,
                "holding_id": staging_holding_id,  # Will be remapped during merge
                "date": txn["trade_date"],
                "type": txn["transaction_type"],
                "quantity": txn["quantity"],
                "price": txn["price"],
                "fees": txn.get("commission", 0),
                "notes": f"IBKR Import - {txn.get('description', '')}",
            },
        )

    @staticmethod
    def _import_dividend_to_staging(db: Session, account_id: int, div: dict) -> None:
        """Import a dividend to staging tables."""
        staging_asset_id = StagedImportService._find_or_create_staging_asset(db, div)
        staging_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, staging_asset_id
        )

        # Check for duplicate
        result = db.execute(
            text("""
                SELECT id FROM staging.transactions
                WHERE staging_holding_id = :holding_id
                AND date = :date
                AND type = 'Dividend'
            """),
            {"holding_id": staging_holding_id, "date": div["date"]},
        )
        if result.fetchone():
            return

        db.execute(
            text("""
                INSERT INTO staging.transactions (
                    staging_holding_id, holding_id, date, type, amount, fees, notes
                ) VALUES (
                    :staging_holding_id, :holding_id, :date, 'Dividend', :amount, 0, :notes
                )
            """),
            {
                "staging_holding_id": staging_holding_id,
                "holding_id": staging_holding_id,
                "date": div["date"],
                "amount": div["amount"],
                "notes": f"IBKR Import - Dividend ${div['amount']:.2f}",
            },
        )

    @staticmethod
    def _import_transfer_to_staging(db: Session, account_id: int, transfer: dict) -> None:
        """Import a transfer (deposit/withdrawal) to staging tables."""
        currency = transfer["currency"]

        # Find or create cash asset
        result = db.execute(
            text("SELECT id FROM staging.assets WHERE symbol = :symbol"),
            {"symbol": currency},
        )
        row = result.fetchone()

        if row:
            staging_asset_id = row[0]
        else:
            result = db.execute(
                text("""
                    INSERT INTO staging.assets (
                        symbol, name, asset_class, currency, data_source,
                        last_fetched_price, is_manual_valuation
                    ) VALUES (
                        :symbol, :name, 'Cash', :currency, 'IBKR', 1, false
                    )
                    RETURNING id
                """),
                {"symbol": currency, "name": f"{currency} Cash", "currency": currency},
            )
            staging_asset_id = result.fetchone()[0]

        staging_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, staging_asset_id
        )

        # Check for duplicate
        result = db.execute(
            text("""
                SELECT id FROM staging.transactions
                WHERE staging_holding_id = :holding_id
                AND date = :date
                AND type = :type
                AND amount = :amount
            """),
            {
                "holding_id": staging_holding_id,
                "date": transfer["date"],
                "type": transfer["type"],
                "amount": transfer["amount"],
            },
        )
        if result.fetchone():
            return

        db.execute(
            text("""
                INSERT INTO staging.transactions (
                    staging_holding_id, holding_id, date, type, amount, fees, notes
                ) VALUES (
                    :staging_holding_id, :holding_id, :date, :type, :amount, 0, :notes
                )
            """),
            {
                "staging_holding_id": staging_holding_id,
                "holding_id": staging_holding_id,
                "date": transfer["date"],
                "type": transfer["type"],
                "amount": transfer["amount"],
                "notes": f"IBKR Import - {transfer.get('description', '')}",
            },
        )

    @staticmethod
    def _import_forex_to_staging(db: Session, account_id: int, forex: dict) -> None:
        """Import a forex conversion to staging tables."""
        from_currency = forex["from_currency"]
        to_currency = forex["to_currency"]

        # Find or create from_currency asset
        result = db.execute(
            text("SELECT id FROM staging.assets WHERE symbol = :symbol"),
            {"symbol": from_currency},
        )
        row = result.fetchone()
        if row:
            from_asset_id = row[0]
        else:
            result = db.execute(
                text("""
                    INSERT INTO staging.assets (
                        symbol, name, asset_class, currency, data_source,
                        last_fetched_price, is_manual_valuation
                    ) VALUES (:symbol, :name, 'Cash', :currency, 'IBKR', 1, false)
                    RETURNING id
                """),
                {
                    "symbol": from_currency,
                    "name": f"{from_currency} Cash",
                    "currency": from_currency,
                },
            )
            from_asset_id = result.fetchone()[0]

        # Find or create to_currency asset
        result = db.execute(
            text("SELECT id FROM staging.assets WHERE symbol = :symbol"),
            {"symbol": to_currency},
        )
        row = result.fetchone()
        if row:
            to_asset_id = row[0]
        else:
            result = db.execute(
                text("""
                    INSERT INTO staging.assets (
                        symbol, name, asset_class, currency, data_source,
                        last_fetched_price, is_manual_valuation
                    ) VALUES (:symbol, :name, 'Cash', :currency, 'IBKR', 1, false)
                    RETURNING id
                """),
                {
                    "symbol": to_currency,
                    "name": f"{to_currency} Cash",
                    "currency": to_currency,
                },
            )
            to_asset_id = result.fetchone()[0]

        from_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, from_asset_id
        )
        to_holding_id = StagedImportService._find_or_create_staging_holding(
            db, account_id, to_asset_id
        )

        # Check for duplicate
        result = db.execute(
            text("""
                SELECT id FROM staging.transactions
                WHERE staging_holding_id = :holding_id
                AND staging_to_holding_id = :to_holding_id
                AND date = :date
                AND type = 'Forex Conversion'
                AND amount = :amount
            """),
            {
                "holding_id": from_holding_id,
                "to_holding_id": to_holding_id,
                "date": forex["date"],
                "amount": forex["from_amount"],
            },
        )
        if result.fetchone():
            return

        from_amount = forex["from_amount"]
        to_amount = forex["to_amount"]
        exchange_rate = to_amount / from_amount if from_amount > 0 else 0

        db.execute(
            text("""
                INSERT INTO staging.transactions (
                    staging_holding_id, holding_id,
                    staging_to_holding_id, to_holding_id,
                    date, type, amount, to_amount, exchange_rate, fees, notes
                ) VALUES (
                    :staging_holding_id, :holding_id,
                    :staging_to_holding_id, :to_holding_id,
                    :date, 'Forex Conversion', :amount, :to_amount, :exchange_rate, 0, :notes
                )
            """),
            {
                "staging_holding_id": from_holding_id,
                "holding_id": from_holding_id,
                "staging_to_holding_id": to_holding_id,
                "to_holding_id": to_holding_id,
                "date": forex["date"],
                "amount": from_amount,
                "to_amount": to_amount,
                "exchange_rate": exchange_rate,
                "notes": f"IBKR Import - Convert {from_amount} {from_currency} to {to_amount} {to_currency}",
            },
        )
