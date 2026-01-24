"""Crypto exchange import service for database operations."""

import logging
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, BrokerDataSource, Holding, Transaction
from app.services.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.coingecko_client import CoinGeckoClient
from app.services.transaction_hash_service import compute_transaction_hash

logger = logging.getLogger(__name__)

FIAT_CURRENCIES = {"USD", "EUR", "ILS", "GBP"}


class CryptoImportService:
    """Service for importing crypto exchange data into the database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def import_data(
        self,
        account_id: int,
        data: BrokerImportData,
        broker_name: str,
        import_positions: bool = False,
        source_id: int | None = None,
    ) -> dict:
        """Import complete crypto broker data into database.

        Args:
            account_id: Account ID to import data for
            data: Parsed broker data
            broker_name: Name of the broker for logging
            import_positions: If True, import positions from API (not recommended).
                              If False (default), calculate balances from transactions.
            source_id: Optional broker source ID for tracking import lineage
        """
        stats = {
            "account_id": account_id,
            "broker": broker_name,
            "start_time": datetime.now().isoformat(),
            "positions": {},
            "transactions": {},
            "cash_transactions": {},
            "dividends": {},
            "holdings_reconstruction": {},
            "errors": [],
        }

        try:
            # Import positions only if explicitly requested (not recommended)
            # Balances should be calculated from transactions instead
            if import_positions and data.positions:
                stats["positions"] = self._import_positions(account_id, data.positions)

            if data.transactions:
                stats["transactions"] = self._import_transactions(
                    account_id, data.transactions, source_id
                )
            if data.cash_transactions:
                stats["cash_transactions"] = self._import_cash_transactions(
                    account_id, data.cash_transactions, source_id
                )
            if data.dividends:
                stats["dividends"] = self._import_dividends(account_id, data.dividends, source_id)

            self.db.commit()

            # Reconstruct holdings from transactions (like Meitav/IBKR do)
            if data.transactions or data.dividends or data.cash_transactions:
                stats["holdings_reconstruction"] = self._reconstruct_and_update_holdings(account_id)
                self.db.commit()

            # Create BrokerDataSource record to track this import
            self._create_broker_data_source(account_id, broker_name, data, stats)
            self.db.commit()

            stats["status"] = "completed"

        except Exception as e:
            logger.exception("%s import failed", broker_name)
            self.db.rollback()
            stats["status"] = "failed"
            stats["errors"].append(str(e))

        stats["end_time"] = datetime.now().isoformat()
        return stats

    def _get_or_create_holding(
        self, account_id: int, symbol: str, asset_class: str, currency: str
    ) -> tuple[Holding, bool]:
        """Get existing holding or create new one with its asset."""
        asset, asset_created = self._find_or_create_asset(symbol, symbol, asset_class, currency)

        holding = (
            self.db.query(Holding)
            .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
            .first()
        )

        if holding:
            return holding, asset_created

        holding = Holding(
            account_id=account_id,
            asset_id=asset.id,
            quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            is_active=False,
        )
        self.db.add(holding)
        self.db.flush()
        return holding, asset_created

    def _import_positions(self, account_id: int, positions: list[ParsedPosition]) -> dict:
        """Import positions as holdings."""
        stats = {
            "total": len(positions),
            "assets_created": 0,
            "holdings_created": 0,
            "holdings_updated": 0,
            "skipped": 0,
            "errors": [],
        }

        for pos in positions:
            try:
                asset, created = self._find_or_create_asset(
                    pos.symbol, pos.symbol, pos.asset_class or "Crypto", pos.currency
                )
                if created:
                    stats["assets_created"] += 1

                holding = (
                    self.db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if holding:
                    holding.quantity = pos.quantity
                    holding.is_active = pos.quantity != 0
                    stats["holdings_updated"] += 1
                else:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=pos.quantity,
                        cost_basis=pos.cost_basis or Decimal("0"),
                        is_active=(pos.quantity != 0),
                    )
                    self.db.add(holding)
                    stats["holdings_created"] += 1

                self.db.flush()

            except Exception as e:
                logger.error(f"Error importing position {pos.symbol}: {e}")
                stats["errors"].append(f"{pos.symbol}: {str(e)}")
                stats["skipped"] += 1

        return stats

    def _import_transactions(
        self, account_id: int, transactions: list[ParsedTransaction], source_id: int | None = None
    ) -> dict:
        """Import buy/sell transactions with hash-based deduplication.

        Uses content hash to detect duplicates. If a duplicate exists under a different
        source, ownership is transferred to the new source (latest-wins policy).
        """
        stats = {
            "total": len(transactions),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        for txn in transactions:
            try:
                holding, asset_created = self._get_or_create_holding(
                    account_id, txn.symbol, "Crypto", txn.currency
                )
                if asset_created:
                    stats["assets_created"] += 1

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=txn.external_transaction_id,
                    txn_date=txn.trade_date,
                    symbol=txn.symbol,
                    txn_type=txn.transaction_type,
                    quantity=txn.quantity or Decimal("0"),
                    price=txn.price_per_unit,
                    fees=txn.fees or Decimal("0"),
                )

                # Check for existing transaction by hash
                existing = (
                    self.db.query(Transaction)
                    .filter(Transaction.content_hash == content_hash)
                    .first()
                )

                if existing:
                    if existing.broker_source_id != source_id:
                        # Transfer ownership to new source
                        existing.broker_source_id = source_id
                        stats["transferred"] += 1
                    else:
                        stats["skipped"] += 1
                    continue

                # Create new transaction with hash
                self.db.add(
                    Transaction(
                        holding_id=holding.id,
                        broker_source_id=source_id,
                        date=txn.trade_date,
                        type=txn.transaction_type,
                        quantity=txn.quantity,
                        price_per_unit=txn.price_per_unit,
                        amount=txn.amount,
                        fees=txn.fees or Decimal("0"),
                        notes=txn.notes,
                        external_transaction_id=txn.external_transaction_id,
                        content_hash=content_hash,
                    )
                )
                self.db.flush()
                stats["imported"] += 1

            except Exception as e:
                logger.error(f"Error importing transaction for {txn.symbol}: {e}")
                stats["errors"].append(f"{txn.symbol}: {str(e)}")

        return stats

    def _import_cash_transactions(
        self,
        account_id: int,
        cash_transactions: list[ParsedCashTransaction],
        source_id: int | None = None,
    ) -> dict:
        """Import cash transactions (deposits, withdrawals) with hash-based deduplication."""
        stats = {
            "total": len(cash_transactions),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "errors": [],
        }

        for cash_txn in cash_transactions:
            try:
                currency = cash_txn.currency
                asset_class = "Cash" if currency in FIAT_CURRENCIES else "Crypto"
                holding, _ = self._get_or_create_holding(
                    account_id, currency, asset_class, currency
                )

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=None,  # Cash transactions don't have external IDs
                    txn_date=cash_txn.date,
                    symbol=currency,
                    txn_type=cash_txn.transaction_type,
                    quantity=cash_txn.amount or Decimal("0"),
                    price=None,
                    fees=cash_txn.fees or Decimal("0"),
                )

                # Check for existing transaction by hash
                existing = (
                    self.db.query(Transaction)
                    .filter(Transaction.content_hash == content_hash)
                    .first()
                )

                if existing:
                    if existing.broker_source_id != source_id:
                        existing.broker_source_id = source_id
                        stats["transferred"] += 1
                    else:
                        stats["skipped"] += 1
                    continue

                self.db.add(
                    Transaction(
                        holding_id=holding.id,
                        broker_source_id=source_id,
                        date=cash_txn.date,
                        type=cash_txn.transaction_type,
                        amount=cash_txn.amount,
                        fees=cash_txn.fees,
                        notes=cash_txn.notes,
                        content_hash=content_hash,
                    )
                )
                self.db.flush()
                stats["imported"] += 1

            except Exception as e:
                logger.error(f"Error importing cash transaction: {e}")
                stats["errors"].append(str(e))

        return stats

    def _import_dividends(
        self, account_id: int, dividends: list[ParsedTransaction], source_id: int | None = None
    ) -> dict:
        """Import dividends/staking rewards with hash-based deduplication."""
        stats = {
            "total": len(dividends),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "errors": [],
        }

        for div in dividends:
            try:
                holding, _ = self._get_or_create_holding(
                    account_id, div.symbol, "Crypto", div.currency
                )

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=div.external_transaction_id,
                    txn_date=div.trade_date,
                    symbol=div.symbol,
                    txn_type=div.transaction_type,
                    quantity=div.quantity or div.amount or Decimal("0"),
                    price=None,
                    fees=div.fees or Decimal("0"),
                )

                # Check for existing transaction by hash
                existing = (
                    self.db.query(Transaction)
                    .filter(Transaction.content_hash == content_hash)
                    .first()
                )

                if existing:
                    if existing.broker_source_id != source_id:
                        existing.broker_source_id = source_id
                        stats["transferred"] += 1
                    else:
                        stats["skipped"] += 1
                    continue

                self.db.add(
                    Transaction(
                        holding_id=holding.id,
                        broker_source_id=source_id,
                        date=div.trade_date,
                        type=div.transaction_type,
                        quantity=div.quantity if div.quantity else div.amount,
                        amount=div.amount,
                        notes=div.notes,
                        external_transaction_id=div.external_transaction_id,
                        content_hash=content_hash,
                    )
                )
                self.db.flush()
                stats["imported"] += 1

            except Exception as e:
                logger.error(f"Error importing dividend for {div.symbol}: {e}")
                stats["errors"].append(f"{div.symbol}: {str(e)}")

        return stats

    def _find_or_create_asset(
        self,
        symbol: str,
        name: str,
        asset_class: str,
        currency: str,
    ) -> tuple[Asset, bool]:
        """Find existing asset or create new one."""
        asset = self.db.query(Asset).filter(Asset.symbol == symbol).first()

        if asset:
            return asset, False

        # For crypto assets, fetch proper name from CoinGecko
        asset_name = name
        category = "Cryptocurrency" if asset_class == "Crypto" else None

        if asset_class == "Crypto":
            try:
                client = CoinGeckoClient()
                coin_info = client.get_coin_info(symbol)
                if coin_info:
                    asset_name = coin_info["name"]
                    logger.info(f"Fetched proper name for {symbol}: {asset_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch coin info for {symbol}, using symbol as name: {e}")

        # Create new asset
        asset = Asset(
            symbol=symbol,
            name=asset_name,
            asset_class=asset_class,
            currency=currency,
            category=category,
        )
        self.db.add(asset)
        self.db.flush()
        logger.info(f"Created new asset: {symbol} ({asset_class})")

        return asset, True

    def _create_broker_data_source(
        self,
        account_id: int,
        broker_name: str,
        data: BrokerImportData,
        stats: dict,
    ) -> BrokerDataSource | None:
        """Create a BrokerDataSource record to track this API import.

        Extracts date range from the imported data and creates a tracking record
        so the Data Coverage card can display this import.

        Args:
            account_id: Account ID
            broker_name: Name of the broker (e.g., 'Kraken')
            data: Parsed broker data
            stats: Import statistics dictionary

        Returns:
            Created BrokerDataSource or None if no data was imported
        """
        all_dates: list[date_type] = (
            [txn.trade_date for txn in data.transactions if txn.trade_date]
            + [cash_txn.date for cash_txn in data.cash_transactions if cash_txn.date]
            + [div.trade_date for div in data.dividends if div.trade_date]
        )

        if all_dates:
            start_date = min(all_dates)
            end_date = max(all_dates)
        else:
            today = date_type.today()
            start_date = today
            end_date = today
            logger.info("No transaction dates found, using today for %s import", broker_name)

        # Calculate total records imported
        total_imported = (
            stats.get("transactions", {}).get("imported", 0)
            + stats.get("cash_transactions", {}).get("imported", 0)
            + stats.get("dividends", {}).get("imported", 0)
        )

        # Create BrokerDataSource record
        broker_source = BrokerDataSource(
            account_id=account_id,
            broker_type=broker_name.lower(),
            source_type="api_fetch",
            source_identifier=f"API Import {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            start_date=start_date,
            end_date=end_date,
            status="completed",
            import_stats={
                "transactions": stats.get("transactions", {}),
                "cash_transactions": stats.get("cash_transactions", {}),
                "dividends": stats.get("dividends", {}),
                "holdings_reconstruction": stats.get("holdings_reconstruction", {}),
                "total_imported": total_imported,
            },
        )
        self.db.add(broker_source)
        self.db.flush()

        logger.info(
            f"Created BrokerDataSource id={broker_source.id} for {broker_name} "
            f"account {account_id}: {start_date} to {end_date}, {total_imported} records"
        )

        return broker_source

    def _reconstruct_and_update_holdings(self, account_id: int) -> dict:
        """Reconstruct holdings from transactions and update the Holding table.

        This replays all transactions to calculate current quantities and cost basis,
        then updates the Holding records accordingly. This is the same approach used
        by Meitav and IBKR imports.

        Args:
            account_id: Account ID to reconstruct holdings for

        Returns:
            Statistics dictionary
        """
        from app.services.portfolio_reconstruction_service import PortfolioReconstructionService

        stats = {
            "holdings_updated": 0,
            "holdings_activated": 0,
            "holdings_deactivated": 0,
        }

        try:
            # Reconstruct holdings as of today
            today = date_type.today()
            reconstructed = PortfolioReconstructionService.reconstruct_holdings(
                self.db, account_id, today, apply_ticker_changes=False
            )

            logger.info(f"Reconstructed {len(reconstructed)} holdings for account {account_id}")

            # Build map of reconstructed holdings by asset_id
            reconstructed_map = {h["asset_id"]: h for h in reconstructed}

            # Get all holdings for this account
            holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

            # Update existing holdings
            for holding in holdings:
                recon = reconstructed_map.get(holding.asset_id)

                if recon:
                    # Update quantity and cost basis from reconstruction
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

                    # Remove from map (processed)
                    del reconstructed_map[holding.asset_id]
                else:
                    # Holding not in reconstruction results - check if it has transactions
                    # If it does, the transactions sum to 0 (otherwise it would be in results)
                    from app.models import Transaction

                    has_transactions = (
                        self.db.query(Transaction)
                        .filter(Transaction.holding_id == holding.id)
                        .first()
                        is not None
                    )

                    if has_transactions:
                        # Has transactions but they sum to 0 - update to 0
                        if holding.quantity != 0:
                            old_qty = holding.quantity
                            holding.quantity = Decimal("0")
                            holding.cost_basis = Decimal("0")
                            holding.is_active = False
                            stats["holdings_deactivated"] += 1
                            stats["holdings_updated"] += 1
                            logger.debug(f"Zeroed holding {holding.asset_id}: was {old_qty}, now 0")
                    else:
                        # No transactions - just mark inactive if already zero
                        if holding.quantity == 0:
                            holding.is_active = False

            # Any remaining in reconstructed_map are new holdings that need to be created
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
