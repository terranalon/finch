"""Meitav Trade import service for database operations.

Handles importing parsed Meitav data into the database,
with Israeli security number resolution via TASE API cache.
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Holding, Transaction
from app.services.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.base_import_service import BaseBrokerImportService
from app.services.tase_api_service import TASEApiService
from app.services.transaction_hash_service import (
    DedupResult,
    check_and_transfer_ownership,
    compute_transaction_hash,
)

logger = logging.getLogger(__name__)


class MeitavImportService(BaseBrokerImportService):
    """Service for importing Meitav Trade broker data into the database.

    Handles:
    - Israeli security number → Yahoo Finance symbol resolution
    - Position import with cost basis
    - Transaction history import
    - Cash transaction import (deposits, withdrawals, interest)
    - Dividend tracking
    """

    @classmethod
    def supported_broker_types(cls) -> list[str]:
        """Return list of broker types this service handles."""
        return ["meitav"]

    def __init__(self, db: Session, broker_type: str) -> None:
        """Initialize with database session and broker type.

        Args:
            db: SQLAlchemy database session
            broker_type: Broker type identifier (e.g., 'meitav')
        """
        super().__init__(db, broker_type)
        self.tase_service = TASEApiService()

    def import_data(
        self, account_id: int, data: BrokerImportData, source_id: int | None = None
    ) -> dict:
        """Import complete Meitav broker data into database.

        Args:
            account_id: Account ID to import into
            data: Parsed broker data from MeitavParser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary with import results
        """
        stats = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "positions": {},
            "transactions": {},
            "cash_transactions": {},
            "dividends": {},
            "errors": [],
        }

        # Count unique assets in file (excluding cash and tax items)
        # Tax codes start with "999" (e.g., "9992975", "9992983")
        def is_real_security(symbol: str) -> bool:
            if not symbol:
                return False
            # Exclude tax codes (start with 999)
            if symbol.startswith("999"):
                return False
            return True

        unique_symbols = set()
        for txn in data.transactions or []:
            if is_real_security(txn.symbol):
                unique_symbols.add(txn.symbol)
        for div in data.dividends or []:
            if is_real_security(div.symbol):
                unique_symbols.add(div.symbol)
        for pos in data.positions or []:
            if is_real_security(pos.symbol):
                unique_symbols.add(pos.symbol)
        stats["unique_assets_in_file"] = len(unique_symbols)
        stats["symbols_in_file"] = list(unique_symbols)

        try:
            # Import positions
            if data.positions:
                stats["positions"] = self._import_positions(account_id, data.positions)

            # Import transactions
            if data.transactions:
                stats["transactions"] = self._import_transactions(
                    account_id, data.transactions, source_id
                )

            # Import cash transactions
            if data.cash_transactions:
                stats["cash_transactions"] = self._import_cash_transactions(
                    account_id, data.cash_transactions, source_id
                )

            # Import dividends
            if data.dividends:
                stats["dividends"] = self._import_dividends(account_id, data.dividends, source_id)

            self.db.commit()

            # Reconstruct holdings from transactions and update the Holding table
            if data.transactions or data.dividends or data.cash_transactions:
                stats["holdings_reconstruction"] = self._reconstruct_and_update_holdings(account_id)
                self.db.commit()

            stats["status"] = "completed"

        except Exception as e:
            logger.exception("Meitav import failed")
            self.db.rollback()
            stats["status"] = "failed"
            stats["errors"].append(str(e))

        stats["end_time"] = datetime.now().isoformat()
        return stats

    def _import_positions(self, account_id: int, positions: list[ParsedPosition]) -> dict:
        """Import positions as holdings.

        Args:
            account_id: Account ID
            positions: List of parsed positions

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(positions),
            "assets_created": 0,
            "holdings_created": 0,
            "holdings_updated": 0,
            "skipped": 0,
            "unresolved_symbols": [],
            "errors": [],
        }

        for pos in positions:
            try:
                # Resolve symbol (TASE:123456 → SYMBOL.TA)
                symbol, tase_number = self._resolve_symbol(pos.symbol)

                if not symbol:
                    stats["unresolved_symbols"].append(pos.symbol)
                    logger.warning(f"Could not resolve symbol: {pos.symbol}")
                    # Continue with the raw symbol for manual resolution
                    symbol = pos.symbol

                # Find or create asset
                asset, created = self._find_or_create_asset(
                    symbol=symbol,
                    name=pos.raw_data.get("security_name", symbol) if pos.raw_data else symbol,
                    asset_class=pos.asset_class or "Stock",
                    currency=pos.currency,
                    tase_security_number=tase_number,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    self.db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if holding:
                    # Update existing holding
                    holding.quantity = pos.quantity
                    holding.cost_basis = pos.cost_basis or Decimal("0")
                    holding.is_active = pos.quantity != 0
                    stats["holdings_updated"] += 1
                    logger.debug(f"Updated holding for {symbol}: qty={pos.quantity}")
                else:
                    # Create new holding
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=pos.quantity,
                        cost_basis=pos.cost_basis or Decimal("0"),
                        is_active=(pos.quantity != 0),
                    )
                    self.db.add(holding)
                    stats["holdings_created"] += 1
                    logger.debug(f"Created holding for {symbol}: qty={pos.quantity}")

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

        Args:
            account_id: Account ID
            transactions: List of parsed transactions
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
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
                # Resolve symbol
                symbol, tase_number = self._resolve_symbol(txn.symbol)

                if not symbol:
                    symbol = txn.symbol

                # Find or create asset
                asset, created = self._find_or_create_asset(
                    symbol=symbol,
                    name=txn.notes or symbol,
                    asset_class="Stock",
                    currency=txn.currency,
                    tase_security_number=tase_number,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    self.db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if not holding:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=False,
                    )
                    self.db.add(holding)
                    self.db.flush()

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=txn.external_transaction_id,
                    txn_date=txn.trade_date,
                    symbol=symbol,
                    txn_type=txn.transaction_type,
                    quantity=txn.quantity or Decimal("0"),
                    price=txn.price_per_unit,
                    fees=txn.fees or Decimal("0"),
                )

                # Check for existing transaction and handle ownership transfer
                dedup_result, _ = check_and_transfer_ownership(self.db, content_hash, source_id)
                if dedup_result != DedupResult.NEW:
                    dedup_result.update_stats(stats)
                    continue

                # Create transaction
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=txn.trade_date,
                    type=txn.transaction_type,
                    quantity=txn.quantity,
                    price_per_unit=txn.price_per_unit,
                    amount=txn.amount,
                    fees=txn.fees,
                    notes=f"Meitav Import - {txn.notes or ''}",
                    external_transaction_id=txn.external_transaction_id,
                    content_hash=content_hash,
                )
                self.db.add(transaction)
                stats["imported"] += 1

                # Create corresponding Trade Settlement for cash impact
                # Buy = cash decreases (negative), Sell = cash increases (positive)
                if txn.amount and txn.transaction_type in ("Buy", "Sell"):
                    cash_symbol = txn.currency  # e.g., "ILS"
                    cash_asset = (
                        self.db.query(Asset)
                        .filter(Asset.symbol == cash_symbol, Asset.asset_class == "Cash")
                        .first()
                    )

                    if cash_asset:
                        cash_holding = (
                            self.db.query(Holding)
                            .filter(
                                Holding.account_id == account_id,
                                Holding.asset_id == cash_asset.id,
                            )
                            .first()
                        )

                        if cash_holding:
                            # For Buy: cash decreases (negative amount)
                            # For Sell: cash increases (positive amount)
                            settlement_amount = (
                                -txn.amount if txn.transaction_type == "Buy" else txn.amount
                            )

                            # Check for duplicate settlement
                            existing_settlement = (
                                self.db.query(Transaction)
                                .filter(
                                    Transaction.holding_id == cash_holding.id,
                                    Transaction.date == txn.trade_date,
                                    Transaction.type == "Trade Settlement",
                                    Transaction.amount == settlement_amount,
                                )
                                .first()
                            )

                            if not existing_settlement:
                                settlement = Transaction(
                                    holding_id=cash_holding.id,
                                    broker_source_id=source_id,
                                    date=txn.trade_date,
                                    type="Trade Settlement",
                                    amount=settlement_amount,
                                    notes=f"Settlement for {txn.transaction_type} {symbol}",
                                )
                                self.db.add(settlement)

                self.db.flush()

            except Exception as e:
                logger.error(f"Error importing transaction {txn.symbol}: {e}")
                stats["errors"].append(f"{txn.symbol}: {str(e)}")

        return stats

    def _import_cash_transactions(
        self,
        account_id: int,
        cash_transactions: list[ParsedCashTransaction],
        source_id: int | None = None,
    ) -> dict:
        """Import cash transactions (deposits, withdrawals, interest) with hash-based dedup.

        Args:
            account_id: Account ID
            cash_transactions: List of parsed cash transactions
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(cash_transactions),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        for cash_txn in cash_transactions:
            try:
                currency = cash_txn.currency

                # Find or create cash asset
                asset, created = self._find_or_create_asset(
                    symbol=currency,
                    name=f"{currency} Cash",
                    asset_class="Cash",
                    currency=currency,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create cash holding
                holding = (
                    self.db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if not holding:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=True,
                    )
                    self.db.add(holding)
                    self.db.flush()

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=None,
                    txn_date=cash_txn.date,
                    symbol=currency,
                    txn_type=cash_txn.transaction_type,
                    quantity=cash_txn.amount or Decimal("0"),
                    price=None,
                    fees=cash_txn.fees or Decimal("0"),
                )

                # Check for existing transaction and handle ownership transfer
                dedup_result, _ = check_and_transfer_ownership(self.db, content_hash, source_id)
                if dedup_result != DedupResult.NEW:
                    dedup_result.update_stats(stats)
                    continue

                # Create transaction
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=cash_txn.date,
                    type=cash_txn.transaction_type,
                    amount=cash_txn.amount,
                    fees=Decimal("0"),
                    notes=f"Meitav Import - {cash_txn.notes or cash_txn.transaction_type}",
                    content_hash=content_hash,
                )
                self.db.add(transaction)
                stats["imported"] += 1

                self.db.flush()

            except Exception as e:
                logger.error(f"Error importing cash transaction: {e}")
                stats["errors"].append(str(e))

        return stats

    def _import_dividends(
        self, account_id: int, dividends: list[ParsedTransaction], source_id: int | None = None
    ) -> dict:
        """Import dividend transactions with hash-based deduplication.

        Args:
            account_id: Account ID
            dividends: List of parsed dividend transactions
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(dividends),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        for div in dividends:
            try:
                # Resolve symbol
                symbol, tase_number = self._resolve_symbol(div.symbol)

                if not symbol:
                    symbol = div.symbol

                # Find or create asset
                asset, created = self._find_or_create_asset(
                    symbol=symbol,
                    name=div.notes or symbol,
                    asset_class="Stock",
                    currency=div.currency,
                    tase_security_number=tase_number,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    self.db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if not holding:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=False,
                    )
                    self.db.add(holding)
                    self.db.flush()

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=div.external_transaction_id,
                    txn_date=div.trade_date,
                    symbol=symbol,
                    txn_type="Dividend",
                    quantity=div.amount or Decimal("0"),
                    price=None,
                    fees=div.fees or Decimal("0"),
                )

                # Check for existing transaction and handle ownership transfer
                dedup_result, _ = check_and_transfer_ownership(self.db, content_hash, source_id)
                if dedup_result != DedupResult.NEW:
                    dedup_result.update_stats(stats)
                    continue

                # Create dividend transaction
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=div.trade_date,
                    type="Dividend",
                    amount=div.amount,
                    fees=Decimal("0"),
                    notes=f"Meitav Import - Dividend {div.amount} {div.currency}",
                    external_transaction_id=div.external_transaction_id,
                    content_hash=content_hash,
                )
                self.db.add(transaction)
                stats["imported"] += 1

                self.db.flush()

            except Exception as e:
                logger.error(f"Error importing dividend {div.symbol}: {e}")
                stats["errors"].append(f"{div.symbol}: {str(e)}")

        return stats

    def _resolve_symbol(self, symbol: str) -> tuple[str | None, str | None]:
        """Resolve TASE security number to Yahoo Finance symbol.

        Args:
            symbol: Symbol in format "TASE:123456" or regular symbol

        Returns:
            Tuple of (resolved_symbol, tase_security_number)
        """
        if not symbol.startswith("TASE:"):
            # Not an Israeli security number, return as-is
            return symbol, None

        # Extract security number
        tase_number = symbol.replace("TASE:", "")

        # Look up in TASE cache
        yahoo_symbol = self.tase_service.get_yahoo_symbol(self.db, tase_number)

        if yahoo_symbol:
            logger.debug(f"Resolved TASE:{tase_number} → {yahoo_symbol}")
            return yahoo_symbol, tase_number

        # Not found in cache - return None to indicate unresolved
        logger.warning(f"TASE security {tase_number} not found in cache")
        return None, tase_number

    def _fetch_yfinance_metadata(self, symbol: str) -> dict | None:
        """Fetch asset metadata from yfinance.

        Args:
            symbol: Yahoo Finance symbol

        Returns:
            Dictionary with name, sector, industry, price or None on error
        """
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            result = {}

            # Get English name (prefer longName over shortName)
            if info.get("longName"):
                result["name"] = info["longName"]
            elif info.get("shortName"):
                result["name"] = info["shortName"]

            # Get sector and industry
            if info.get("sector"):
                result["sector"] = info["sector"]
            if info.get("industry"):
                result["industry"] = info["industry"]

            # Get quote type to determine asset class (EQUITY, ETF, MUTUALFUND, etc.)
            if info.get("quoteType"):
                result["quoteType"] = info["quoteType"]

            # Get current price (try multiple fields in order of preference)
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )

            if price and price > 0:
                # Convert from Agorot to ILS for Israeli stocks
                if symbol.endswith(".TA"):
                    price = price / 100
                result["price"] = Decimal(str(price))

            logger.debug(f"Fetched yfinance metadata for {symbol}: {result}")
            return result if result else None

        except Exception as e:
            logger.warning(f"Failed to fetch yfinance metadata for {symbol}: {e}")
            return None

    def _find_or_create_asset(
        self,
        symbol: str,
        name: str,
        asset_class: str,
        currency: str,
        tase_security_number: str | None = None,
    ) -> tuple[Asset, bool]:
        """Find or create an asset.

        Args:
            symbol: Yahoo Finance compatible symbol
            name: Asset name
            asset_class: Asset class (Stock, ETF, Cash, etc.)
            currency: Asset currency
            tase_security_number: Israeli security number (if applicable)

        Returns:
            Tuple of (asset, created)
        """
        # Try to find by symbol first
        asset = self.db.query(Asset).filter(Asset.symbol == symbol).first()

        if asset:
            # Update tase_security_number if provided and missing
            if tase_security_number and not asset.tase_security_number:
                asset.tase_security_number = tase_security_number
                logger.debug(f"Updated TASE security number for {symbol}")
            return asset, False

        # Try to find by TASE security number
        if tase_security_number:
            asset = (
                self.db.query(Asset)
                .filter(Asset.tase_security_number == tase_security_number)
                .first()
            )
            if asset:
                # Update symbol if it was a placeholder
                if asset.symbol.startswith("TASE:"):
                    asset.symbol = symbol
                    logger.info(f"Updated symbol for TASE:{tase_security_number} → {symbol}")
                return asset, False

        # Create new asset
        logger.info(f"Creating new asset: {symbol} ({name})")

        # For Cash assets, set price to 1
        last_price = Decimal("1") if asset_class == "Cash" else None
        last_fetched = datetime.now() if asset_class == "Cash" else None

        # Fetch additional metadata from yfinance for tradeable assets (not Cash or Tax)
        english_name = name
        category = None
        industry = None
        if asset_class not in ("Cash", "Tax") and symbol:
            yf_metadata = self._fetch_yfinance_metadata(symbol)
            if yf_metadata:
                # Prefer English name from yfinance
                english_name = yf_metadata.get("name") or name
                category = yf_metadata.get("sector")
                industry = yf_metadata.get("industry")
                # Use yfinance quoteType to determine correct asset class
                quote_type = yf_metadata.get("quoteType")
                if quote_type == "ETF":
                    asset_class = "ETF"
                elif quote_type == "MUTUALFUND":
                    asset_class = "MutualFund"
                elif quote_type == "EQUITY":
                    asset_class = "Stock"
                # Update price if fetched
                if yf_metadata.get("price"):
                    last_price = yf_metadata["price"]
                    last_fetched = datetime.now()

        asset = Asset(
            symbol=symbol,
            name=english_name,
            asset_class=asset_class,
            currency=currency,
            category=category,
            industry=industry,
            data_source="Meitav",
            tase_security_number=tase_security_number,
            last_fetched_price=last_price,
            last_fetched_at=last_fetched,
            is_manual_valuation=False,  # We have price from yfinance
        )

        self.db.add(asset)
        self.db.flush()

        logger.info(f"Created asset {symbol} with ID {asset.id}")
        return asset, True

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
