"""Israeli securities import service for database operations.

Handles importing parsed data from Israeli brokers (Meitav, Bank Hapoalim)
into the database, with Israeli security number resolution via TASE API cache.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Holding, Transaction
from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.brokers.base_import_service import BaseBrokerImportService
from app.services.brokers.shared.tase_api_service import TASEApiService
from app.services.shared.transaction_hash_service import (
    DedupResult,
    check_and_transfer_ownership,
    compute_transaction_hash,
)

logger = logging.getLogger(__name__)


def _is_real_security(symbol: str) -> bool:
    """Check if symbol represents a real security (not a tax code or empty).

    Tax codes are prefixed with "TAX:" by the parser.
    """
    if not symbol:
        return False
    return not symbol.startswith("TAX:")


def _normalize_to_datetime(value: datetime | date | None) -> datetime | None:
    """Convert a date or datetime to datetime. Returns None if input is None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


class IsraeliSecuritiesImportService(BaseBrokerImportService):
    """Service for importing Israeli broker data into the database.

    Supports: Meitav Trade, Bank Hapoalim, and other Israeli brokers.

    Handles:
    - Israeli security number -> Yahoo Finance symbol resolution
    - Position import with cost basis
    - Transaction history import
    - Cash transaction import (deposits, withdrawals, interest)
    - Dividend tracking
    """

    @classmethod
    def supported_broker_types(cls) -> list[str]:
        """Return list of broker types this service handles."""
        return ["meitav", "bank_hapoalim"]

    def __init__(self, db: Session, broker_type: str) -> None:
        """Initialize with database session and broker type.

        Args:
            db: SQLAlchemy database session
            broker_type: Broker type identifier (e.g., 'meitav', 'bank_hapoalim')
        """
        super().__init__(db, broker_type)
        self.tase_service = TASEApiService()
        # Get broker name from registry for dynamic notes
        from app.services.brokers.broker_parser_registry import BrokerParserRegistry

        parser = BrokerParserRegistry.get_parser(broker_type)
        self._broker_name = parser.broker_name()

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

        # Collect unique assets from all data sources (excluding tax codes)
        all_items = (data.transactions or []) + (data.dividends or []) + (data.positions or [])
        unique_symbols = {item.symbol for item in all_items if _is_real_security(item.symbol)}
        stats["unique_assets_in_file"] = len(unique_symbols)
        stats["symbols_in_file"] = list(unique_symbols)

        try:
            # Import positions
            if data.positions:
                stats["positions"] = self._import_positions(account_id, data.positions)

            # Import cash transactions FIRST to ensure cash holdings exist
            # (required for Trade Settlements in dual-entry accounting)
            if data.cash_transactions:
                stats["cash_transactions"] = self._import_cash_transactions(
                    account_id, data.cash_transactions, source_id
                )

            # Import transactions AFTER cash holdings exist
            if data.transactions:
                stats["transactions"] = self._import_transactions(
                    account_id, data.transactions, source_id
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
            logger.exception(f"{self._broker_name} import failed")
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
                # Calculate fallback price from cost basis if available
                fallback_price = None
                if pos.cost_basis and pos.quantity and pos.quantity > 0:
                    fallback_price = pos.cost_basis / pos.quantity

                asset, created = self._find_or_create_asset(
                    symbol=symbol,
                    name=pos.raw_data.get("security_name", symbol) if pos.raw_data else symbol,
                    asset_class=pos.asset_class or "Stock",
                    currency=pos.currency,
                    tase_security_number=tase_number,
                    fallback_price=fallback_price,
                    fallback_price_date=datetime.now(),  # Positions are current state
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
                    fallback_price=txn.price_per_unit,
                    fallback_price_date=txn.trade_date,
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
                    notes=f"{self._broker_name} Import - {txn.notes or ''}",
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
                    notes=f"{self._broker_name} Import - {cash_txn.notes or cash_txn.transaction_type}",
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
                    notes=f"{self._broker_name} Import - Dividend {div.amount} {div.currency}",
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

    def _maybe_update_fallback_price(
        self,
        asset: Asset,
        fallback_price: Decimal | None,
        fallback_price_date: datetime | None,
    ) -> bool:
        """Update asset's fallback price if the new price is more recent.

        For unresolved TASE symbols (mutual funds), updates the price if:
        - The asset has no price yet, OR
        - The new price date is more recent than the existing price date

        Args:
            asset: The asset to potentially update
            fallback_price: The new price from a transaction
            fallback_price_date: The date of the transaction

        Returns:
            True if the price was updated, False otherwise
        """
        if not asset.symbol or not asset.symbol.startswith("TASE:"):
            return False

        if not fallback_price or fallback_price <= 0:
            return False

        price_datetime = _normalize_to_datetime(fallback_price_date)

        has_no_price = not asset.last_fetched_price or asset.last_fetched_price == 0
        has_no_existing_date = not asset.last_fetched_at
        # Safe comparison - only compare if existing_date is a real datetime
        is_more_recent = (
            price_datetime is not None
            and isinstance(asset.last_fetched_at, datetime)
            and price_datetime > asset.last_fetched_at
        )

        if not has_no_price and not has_no_existing_date and not is_more_recent:
            return False

        asset.last_fetched_price = fallback_price
        asset.last_fetched_at = price_datetime or datetime.now()
        asset.is_manual_valuation = True
        logger.info(
            f"Updated {asset.symbol} with fallback price {fallback_price} "
            f"from {fallback_price_date}"
        )
        return True

    def _find_or_create_asset(
        self,
        symbol: str,
        name: str,
        asset_class: str,
        currency: str,
        tase_security_number: str | None = None,
        fallback_price: Decimal | None = None,
        fallback_price_date: datetime | None = None,
    ) -> tuple[Asset, bool]:
        """Find or create an asset.

        Args:
            symbol: Yahoo Finance compatible symbol or TASE:xxxxx for unresolved
            name: Asset name
            asset_class: Asset class (Stock, ETF, Cash, etc.)
            currency: Asset currency
            tase_security_number: Israeli security number (if applicable)
            fallback_price: Price to use if symbol can't be resolved (e.g., mutual funds)
            fallback_price_date: Date of the fallback price (for recency comparison)

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

            # Update price for unresolved TASE symbols if we have a more recent price
            self._maybe_update_fallback_price(asset, fallback_price, fallback_price_date)

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

                # Update price for unresolved TASE symbols if we have a more recent price
                self._maybe_update_fallback_price(asset, fallback_price, fallback_price_date)

                return asset, False

        # Create new asset
        logger.info(f"Creating new asset: {symbol} ({name})")

        # Check if this is an unresolved TASE symbol (e.g., mutual funds not in TASE cache)
        is_unresolved_tase = symbol.startswith("TASE:")

        # For Cash assets, set price to 1
        last_price = Decimal("1") if asset_class == "Cash" else None
        last_fetched = datetime.now() if asset_class == "Cash" else None
        is_manual = False

        english_name = name
        category = None
        industry = None

        if is_unresolved_tase:
            # Unresolved TASE symbol (typically mutual funds not on Yahoo Finance)
            # Use fallback price from transaction and mark as manual valuation
            if fallback_price and fallback_price > 0:
                last_price = fallback_price
                last_fetched = _normalize_to_datetime(fallback_price_date) or datetime.now()
            is_manual = True
            asset_class = "MutualFund"  # Most unresolved Israeli securities are mutual funds
            logger.info(
                f"Unresolved TASE symbol {symbol} - using fallback price {fallback_price} "
                f"from {fallback_price_date}, marked as manual valuation"
            )
        elif asset_class not in ("Cash", "Tax") and symbol:
            # Fetch additional metadata from yfinance for tradeable assets
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
            data_source=self._broker_name,
            tase_security_number=tase_security_number,
            last_fetched_price=last_price,
            last_fetched_at=last_fetched,
            is_manual_valuation=is_manual,
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
        from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings

        return reconstruct_and_update_holdings(self.db, account_id)
