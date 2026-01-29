"""Crypto exchange import service for database operations."""

import logging
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, BrokerDataSource, Holding
from app.services.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.base_import_service import (
    BaseBrokerImportService,
    extract_date_range_serializable,
)
from app.services.coingecko_client import CoinGeckoClient
from app.services.transaction_hash_service import create_or_transfer_transaction

logger = logging.getLogger(__name__)

FIAT_CURRENCIES = {"USD", "EUR", "ILS", "GBP"}


class CryptoImportService(BaseBrokerImportService):
    """Service for importing crypto exchange data into the database."""

    @classmethod
    def supported_broker_types(cls) -> list[str]:
        """Return list of broker types this service handles."""
        return ["kraken", "bit2c", "binance"]

    def __init__(self, db: Session, broker_type: str) -> None:
        """Initialize with database session and broker type.

        Args:
            db: SQLAlchemy database session
            broker_type: Broker type identifier (e.g., 'kraken', 'bit2c', 'binance')
        """
        super().__init__(db, broker_type)

    def import_data(
        self,
        account_id: int,
        data: BrokerImportData,
        source_id: int | None = None,
        import_positions: bool = False,
    ) -> dict:
        """Import complete crypto broker data into database.

        Args:
            account_id: Account ID to import data for
            data: Parsed broker data
            source_id: Optional broker source ID for tracking import lineage
            import_positions: If True, import positions from API (not recommended).
                              If False (default), calculate balances from transactions.
        """
        stats = {
            "account_id": account_id,
            "broker": self.broker_type.capitalize(),
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
            self._create_broker_data_source(account_id, self.broker_type.capitalize(), data, stats)
            self.db.commit()

            # Calculate date range from imported data for snapshot generation
            all_dates = (
                [txn.trade_date for txn in data.transactions]
                + [cash_txn.date for cash_txn in data.cash_transactions]
                + [div.trade_date for div in data.dividends]
            )
            date_range = extract_date_range_serializable(all_dates)
            if date_range:
                stats["date_range"] = date_range

            stats["status"] = "completed"

        except Exception as e:
            logger.exception("%s import failed", self.broker_type)
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

                # Create or transfer transaction with automatic deduplication
                result, _ = create_or_transfer_transaction(
                    db=self.db,
                    holding_id=holding.id,
                    source_id=source_id,
                    txn_date=txn.trade_date,
                    txn_type=txn.transaction_type,
                    symbol=txn.symbol,
                    quantity=txn.quantity,
                    price=txn.price_per_unit,
                    fees=txn.fees,
                    amount=txn.amount,
                    external_txn_id=txn.external_transaction_id,
                    notes=txn.notes,
                )
                result.update_stats(stats)

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

                # Create or transfer transaction with automatic deduplication
                result, _ = create_or_transfer_transaction(
                    db=self.db,
                    holding_id=holding.id,
                    source_id=source_id,
                    txn_date=cash_txn.date,
                    txn_type=cash_txn.transaction_type,
                    symbol=currency,
                    amount=cash_txn.amount,
                    fees=cash_txn.fees,
                    notes=cash_txn.notes,
                )
                result.update_stats(stats)

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

                # Create or transfer transaction with automatic deduplication
                result, _ = create_or_transfer_transaction(
                    db=self.db,
                    holding_id=holding.id,
                    source_id=source_id,
                    txn_date=div.trade_date,
                    txn_type=div.transaction_type,
                    symbol=div.symbol,
                    quantity=div.quantity,
                    amount=div.amount,
                    fees=div.fees,
                    external_txn_id=div.external_transaction_id,
                    notes=div.notes,
                )
                result.update_stats(stats)

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
        then updates the Holding records accordingly.

        Args:
            account_id: Account ID to reconstruct holdings for

        Returns:
            Statistics dictionary
        """
        from app.services.holdings_reconstruction import reconstruct_and_update_holdings

        return reconstruct_and_update_holdings(self.db, account_id)
