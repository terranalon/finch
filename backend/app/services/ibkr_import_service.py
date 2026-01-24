"""IBKR import helper service.

This service provides helper methods for importing IBKR data into the portfolio tracker.
The main import orchestration is handled by IBKRFlexImportService using the Flex Query API.
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Holding, Transaction
from app.services.asset_metadata_service import AssetMetadataService
from app.services.price_fetcher import PriceFetcher
from app.services.transaction_hash_service import compute_transaction_hash

logger = logging.getLogger(__name__)


class IBKRImportService:
    """Helper service for importing IBKR data components (positions, transactions, dividends)."""

    @staticmethod
    def _import_positions(db: Session, account_id: int, positions: list[dict]) -> dict:
        """
        Import positions as holdings.

        For each position:
        1. Find or auto-create asset
        2. Find or create holding
        3. Update holding quantity and cost_basis

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            positions: List of position dicts from parser

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(positions),
            "assets_created": 0,
            "holdings_created": 0,
            "holdings_updated": 0,
            "skipped": 0,
            "errors": [],
            "forex_pairs_skipped": 0,
        }

        # Filter out forex pair positions (e.g., USD.ILS, USD.CAD)
        # These are IBKR tracking records, not real holdings
        currency_codes = {
            "USD",
            "CAD",
            "ILS",
            "EUR",
            "GBP",
            "JPY",
            "CHF",
            "AUD",
            "NZD",
            "SEK",
            "NOK",
            "DKK",
        }

        # Collect new holdings for batch add
        new_holdings = []

        for pos in positions:
            try:
                # Skip forex pair assets (e.g., USD.CAD, USD.ILS)
                symbol = pos["symbol"]
                if "." in symbol:
                    parts = symbol.split(".")
                    if (
                        len(parts) == 2
                        and parts[0] in currency_codes
                        and parts[1] in currency_codes
                    ):
                        stats["forex_pairs_skipped"] += 1
                        logger.debug(
                            f"Skipping forex pair position: {symbol} qty={pos['quantity']}"
                        )
                        continue

                # Find or create asset
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=pos["symbol"],
                    name=pos["description"],
                    asset_class=pos["asset_class"],
                    currency=pos.get("currency", "USD"),
                    ibkr_symbol=pos["original_symbol"],
                    cusip=pos.get("cusip"),
                    isin=pos.get("isin"),
                    conid=pos.get("conid"),
                    figi=pos.get("figi"),
                )

                if created:
                    stats["assets_created"] += 1

                if pos["needs_validation"]:
                    logger.warning(f"Asset {pos['symbol']} needs validation with Yahoo Finance")

                # Find or create holding
                holding = (
                    db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if holding:
                    # Update existing holding
                    holding.quantity = pos["quantity"]
                    holding.cost_basis = pos["cost_basis"]
                    holding.is_active = pos["quantity"] != 0
                    stats["holdings_updated"] += 1
                    logger.debug(f"Updated holding for {pos['symbol']}: qty={pos['quantity']}")
                else:
                    # Create new holding - add to batch list
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=pos["quantity"],
                        cost_basis=pos["cost_basis"],
                        is_active=(pos["quantity"] != 0),
                    )
                    new_holdings.append(holding)
                    stats["holdings_created"] += 1
                    logger.debug(f"Created holding for {pos['symbol']}: qty={pos['quantity']}")

            except Exception as e:
                logger.error(f"Error importing position {pos.get('symbol')}: {str(e)}")
                stats["errors"].append(f"{pos.get('symbol')}: {str(e)}")
                stats["skipped"] += 1
                continue

        # Batch add all new holdings at once
        if new_holdings:
            db.add_all(new_holdings)
            db.flush()

        return stats

    @staticmethod
    def _import_cash_balances(db: Session, account_id: int, cash_balances: list[dict]) -> dict:
        """
        Import cash balances as special holdings.

        Cash is represented as assets with currency code symbols.
        For example: "USD", "CAD", "EUR", "ILS"

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            cash_balances: List of cash balance dicts from parser

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(cash_balances),
            "assets_created": 0,
            "holdings_created": 0,
            "holdings_updated": 0,
            "migrated": 0,
            "errors": [],
        }

        # Collect new assets and holdings for batch operations
        new_assets = []
        new_holdings = []

        for cash in cash_balances:
            try:
                symbol = cash["symbol"]  # e.g., "USD", "CAD", "EUR"
                currency = cash["currency"]
                balance = cash["balance"]

                # Check for old-format cash asset (CASH-USD) and migrate
                old_symbol = f"CASH-{currency}"
                old_asset = db.query(Asset).filter(Asset.symbol == old_symbol).first()

                if old_asset:
                    # Migrate old asset to new naming
                    logger.info(f"Migrating old cash asset {old_symbol} -> {symbol}")
                    old_asset.symbol = symbol
                    old_asset.name = cash["description"]
                    old_asset.last_fetched_price = Decimal("1")
                    old_asset.last_fetched_at = datetime.now()
                    asset = old_asset
                    stats["migrated"] += 1
                else:
                    # Find or create new-format cash asset
                    asset = db.query(Asset).filter(Asset.symbol == symbol).first()

                    if not asset:
                        # Create new cash asset
                        asset = Asset(
                            symbol=symbol,
                            name=cash["description"],
                            asset_class=cash["asset_class"],  # "Cash"
                            currency=currency,
                            data_source="IBKR",
                            last_fetched_price=Decimal("1"),  # Cash always has price=1
                            last_fetched_at=datetime.now(),
                            is_manual_valuation=False,
                        )
                        new_assets.append(asset)
                        stats["assets_created"] += 1
                        logger.info(f"Created cash asset: {symbol}")
                    else:
                        # Update last_fetched_price to ensure it's 1
                        asset.last_fetched_price = Decimal("1")
                        asset.last_fetched_at = datetime.now()

            except Exception as e:
                logger.error(f"Error importing cash balance {cash.get('symbol')}: {str(e)}")
                stats["errors"].append(f"{cash.get('symbol')}: {str(e)}")
                continue

        # Batch add new assets and flush to get IDs
        if new_assets:
            db.add_all(new_assets)
            db.flush()

        # Now process holdings (assets have IDs now)
        for cash in cash_balances:
            try:
                symbol = cash["symbol"]
                balance = cash["balance"]

                # Find the asset (either existing or newly created)
                asset = db.query(Asset).filter(Asset.symbol == symbol).first()
                if not asset:
                    continue

                # Find or create holding
                holding = (
                    db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if holding:
                    # Update existing holding
                    holding.quantity = balance
                    holding.cost_basis = balance  # For cash, cost_basis = balance
                    holding.is_active = balance != 0
                    stats["holdings_updated"] += 1
                    logger.debug(f"Updated cash holding for {symbol}: {balance}")
                else:
                    # Create new holding - add to batch list
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=balance,
                        cost_basis=balance,  # For cash, cost_basis = balance
                        is_active=(balance != 0),
                    )
                    new_holdings.append(holding)
                    stats["holdings_created"] += 1
                    logger.debug(f"Created cash holding for {symbol}: {balance}")

            except Exception as e:
                logger.error(f"Error creating holding for {cash.get('symbol')}: {str(e)}")
                stats["errors"].append(f"{cash.get('symbol')}: {str(e)}")
                continue

        # Batch add all new holdings at once
        if new_holdings:
            db.add_all(new_holdings)
            db.flush()

        return stats

    @staticmethod
    def _import_fx_positions(
        db: Session, account_id: int, fx_positions: dict[str, "Decimal"]
    ) -> dict:
        """
        Import cash positions from FxPositions.

        FxPositions is IBKR's authoritative source for cash balances by currency.
        This is more reliable than CashReport section which may not be in all Flex Queries.

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            fx_positions: Dict of {currency: balance} from parser

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(fx_positions),
            "assets_created": 0,
            "holdings_created": 0,
            "holdings_updated": 0,
            "errors": [],
        }

        currency_names = {
            "USD": "United States Dollar",
            "CAD": "Canadian Dollar",
            "ILS": "Israeli Shekel",
            "EUR": "Euro",
            "GBP": "British Pound",
            "JPY": "Japanese Yen",
            "CHF": "Swiss Franc",
            "AUD": "Australian Dollar",
        }

        # Collect new assets and holdings for batch operations
        new_assets = []
        new_holdings = []

        # First pass: create any missing assets
        for currency, balance in fx_positions.items():
            try:
                asset = db.query(Asset).filter(Asset.symbol == currency).first()

                if not asset:
                    asset = Asset(
                        symbol=currency,
                        name=currency_names.get(currency, f"{currency} Cash"),
                        asset_class="Cash",
                        currency=currency,
                        data_source="IBKR",
                        last_fetched_price=Decimal("1"),
                        last_fetched_at=datetime.now(),
                        is_manual_valuation=False,
                    )
                    new_assets.append(asset)
                    stats["assets_created"] += 1
                    logger.info(f"Created cash asset: {currency}")
                else:
                    asset.last_fetched_price = Decimal("1")
                    asset.last_fetched_at = datetime.now()

            except Exception as e:
                logger.error(f"Error creating asset for {currency}: {str(e)}")
                stats["errors"].append(f"{currency}: {str(e)}")
                continue

        # Batch add new assets and flush to get IDs
        if new_assets:
            db.add_all(new_assets)
            db.flush()

        # Second pass: create/update holdings (assets have IDs now)
        for currency, balance in fx_positions.items():
            try:
                asset = db.query(Asset).filter(Asset.symbol == currency).first()
                if not asset:
                    continue

                holding = (
                    db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == asset.id)
                    .first()
                )

                if holding:
                    holding.quantity = balance
                    holding.cost_basis = balance
                    holding.is_active = balance != 0
                    stats["holdings_updated"] += 1
                    logger.info(f"Updated cash holding {currency}: {balance:.2f}")
                else:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=balance,
                        cost_basis=balance,
                        is_active=(balance != 0),
                    )
                    new_holdings.append(holding)
                    stats["holdings_created"] += 1
                    logger.info(f"Created cash holding {currency}: {balance:.2f}")

            except Exception as e:
                logger.error(f"Error importing FxPosition {currency}: {str(e)}")
                stats["errors"].append(f"{currency}: {str(e)}")
                continue

        # Batch add all new holdings at once
        if new_holdings:
            db.add_all(new_holdings)
            db.flush()

        return stats

    @staticmethod
    def _import_stmt_funds_balances(
        db: Session, account_id: int, balances: list[dict], source_id: int
    ) -> dict:
        """
        Import daily cash balances from StmtFunds (Statement of Funds).

        This stores IBKR's authoritative daily cash balances by currency.
        Use these for historical reconstruction instead of summing transactions.

        Args:
            db: Database session
            account_id: Our account ID
            balances: List of balance records from parser
            source_id: BrokerDataSource ID for linking

        Returns:
            Statistics dictionary
        """
        from app.models import DailyCashBalance

        stats = {
            "total": len(balances),
            "inserted": 0,
            "updated": 0,
            "errors": [],
        }

        for balance_record in balances:
            try:
                date_val = balance_record["date"]
                currency = balance_record["currency"]
                balance = balance_record["balance"]
                activity = balance_record.get("activity", "")

                # Check if record exists
                existing = (
                    db.query(DailyCashBalance)
                    .filter(
                        DailyCashBalance.account_id == account_id,
                        DailyCashBalance.date == date_val,
                        DailyCashBalance.currency == currency,
                    )
                    .first()
                )

                if existing:
                    # Update existing record
                    existing.balance = balance
                    existing.activity = activity
                    existing.broker_source_id = source_id
                    stats["updated"] += 1
                else:
                    # Insert new record
                    new_balance = DailyCashBalance(
                        account_id=account_id,
                        date=date_val,
                        currency=currency,
                        balance=balance,
                        activity=activity,
                        broker_source_id=source_id,
                    )
                    db.add(new_balance)
                    stats["inserted"] += 1

                # Commit in batches
                if (stats["inserted"] + stats["updated"]) % 100 == 0:
                    db.flush()

            except Exception as e:
                logger.error(f"Error importing StmtFunds balance for {balance_record}: {str(e)}")
                stats["errors"].append(f"{balance_record}: {str(e)}")
                continue

        db.flush()
        logger.info(
            f"Imported StmtFunds balances: {stats['inserted']} new, {stats['updated']} updated"
        )
        return stats

    @staticmethod
    def _mark_stale_holdings_inactive(
        db: Session, account_id: int, current_symbols: set[str]
    ) -> dict:
        """
        Mark holdings as inactive if they're not in the current position list.

        This handles the case where a position was sold (qty=0) but we don't
        have an explicit position record for it in the Flex Query.

        Args:
            db: Database session
            account_id: Our account ID
            current_symbols: Set of symbols that are currently held

        Returns:
            Statistics dictionary
        """
        stats = {"marked_inactive": 0, "symbols": []}

        # Get all active stock holdings for this account
        active_holdings = (
            db.query(Holding)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(
                Holding.account_id == account_id,
                Holding.is_active == True,  # noqa: E712
                Asset.asset_class == "Stock",  # Only check stocks, not cash
            )
            .all()
        )

        for holding in active_holdings:
            asset = db.query(Asset).filter(Asset.id == holding.asset_id).first()
            if asset and asset.symbol not in current_symbols:
                holding.is_active = False
                holding.quantity = Decimal("0")
                stats["marked_inactive"] += 1
                stats["symbols"].append(asset.symbol)
                logger.info(f"Marked stale holding as inactive: {asset.symbol}")

        if stats["marked_inactive"] > 0:
            logger.info(
                f"Marked {stats['marked_inactive']} stale holdings as inactive: {stats['symbols']}"
            )

        return stats

    @staticmethod
    def _import_transactions(
        db: Session, account_id: int, transactions: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import trades as transactions.

        For each trade:
        1. Find or auto-create asset
        2. Find or create holding
        3. Check for duplicates
        4. Create transaction

        Uses batch operations to minimize database lock time.

        Note: Does NOT apply FIFO logic - that should be done separately
        or transactions should be created via the existing transaction endpoint.

        Args:
            db: Database session
            account_id: Our account ID
            transactions: List of transaction dicts from parser
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
            "forex_pairs_skipped": 0,
        }

        # Filter out forex pair transactions (e.g., USD.ILS, USD.CAD)
        # These are IBKR tracking records, not real trades
        # The actual forex conversions are captured in FxTransactions
        currency_codes = {
            "USD",
            "CAD",
            "ILS",
            "EUR",
            "GBP",
            "JPY",
            "CHF",
            "AUD",
            "NZD",
            "SEK",
            "NOK",
            "DKK",
        }

        # Collect new transactions for batch operations
        new_transactions = []

        for txn in transactions:
            try:
                # Skip forex pair assets (e.g., USD.CAD, USD.ILS)
                symbol = txn["symbol"]
                if "." in symbol:
                    parts = symbol.split(".")
                    if (
                        len(parts) == 2
                        and parts[0] in currency_codes
                        and parts[1] in currency_codes
                    ):
                        stats["forex_pairs_skipped"] += 1
                        logger.debug(
                            f"Skipping forex pair transaction: {symbol} {txn['transaction_type']} {txn['quantity']}"
                        )
                        continue

                # Find or create asset
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=txn["symbol"],
                    name=txn["description"],
                    asset_class=txn["asset_class"],
                    currency=txn.get("currency", "USD"),
                    ibkr_symbol=txn["original_symbol"],
                    cusip=txn.get("cusip"),
                    isin=txn.get("isin"),
                    conid=txn.get("conid"),
                    figi=txn.get("figi"),
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    db.query(Holding)
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
                    db.add(holding)
                    db.flush()  # Need ID for transaction FK

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=txn.get("external_transaction_id"),
                    txn_date=txn["trade_date"],
                    symbol=txn["symbol"],
                    txn_type=txn["transaction_type"],
                    quantity=txn["quantity"],
                    price=txn["price"],
                    fees=txn["commission"],
                )

                # Check for existing transaction by hash
                existing = (
                    db.query(Transaction).filter(Transaction.content_hash == content_hash).first()
                )

                if existing:
                    if existing.broker_source_id != source_id:
                        existing.broker_source_id = source_id
                        stats["transferred"] += 1
                    else:
                        stats["skipped"] += 1
                    continue

                # Create transaction - add to batch list
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=txn["trade_date"],
                    type=txn["transaction_type"],
                    quantity=txn["quantity"],
                    price_per_unit=txn["price"],
                    fees=txn["commission"],
                    notes=f"IBKR Import - {txn['description']}",
                    external_transaction_id=txn.get("external_transaction_id"),
                    content_hash=content_hash,
                )
                new_transactions.append(transaction)
                stats["imported"] += 1
                logger.debug(
                    f"Created transaction for {txn['symbol']}: {txn['transaction_type']} {txn['quantity']} @ {txn['price']}"
                )

                # Create cash transaction for trade settlement (netCash)
                net_cash = txn.get("net_cash")
                if net_cash and net_cash != 0:
                    trade_currency = txn.get("currency", "USD")

                    # Find or create cash asset
                    cash_asset, _ = IBKRImportService._find_or_create_asset(
                        db,
                        symbol=trade_currency,
                        name=f"{trade_currency} Cash",
                        asset_class="Cash",
                        currency=trade_currency,
                    )

                    # Find or create cash holding
                    cash_holding = (
                        db.query(Holding)
                        .filter(Holding.account_id == account_id, Holding.asset_id == cash_asset.id)
                        .first()
                    )

                    if not cash_holding:
                        cash_holding = Holding(
                            account_id=account_id,
                            asset_id=cash_asset.id,
                            quantity=Decimal("0"),
                            cost_basis=Decimal("0"),
                            is_active=True,
                        )
                        db.add(cash_holding)
                        db.flush()  # Need ID for transaction FK

                    # Check for duplicate cash transaction
                    existing_cash_txn = (
                        db.query(Transaction)
                        .filter(
                            Transaction.holding_id == cash_holding.id,
                            Transaction.date == txn["trade_date"],
                            Transaction.type == "Trade Settlement",
                            Transaction.amount == net_cash,
                        )
                        .first()
                    )

                    if not existing_cash_txn:
                        # Create Trade Settlement transaction - add to batch list
                        cash_transaction = Transaction(
                            holding_id=cash_holding.id,
                            broker_source_id=source_id,
                            date=txn["trade_date"],
                            type="Trade Settlement",
                            amount=net_cash,
                            notes=f"Cash settlement for {txn['symbol']} {txn['transaction_type']}",
                        )
                        new_transactions.append(cash_transaction)
                        logger.debug(
                            f"Created cash settlement: {trade_currency} {net_cash} for {txn['symbol']}"
                        )

            except Exception as e:
                logger.error(f"Error importing transaction {txn.get('symbol')}: {str(e)}")
                stats["errors"].append(f"{txn.get('symbol')}: {str(e)}")
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _import_dividends(
        db: Session, account_id: int, dividends: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import dividends as transactions with hash-based deduplication.

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            dividends: List of dividend dicts from parser
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

        # Collect new transactions for batch add
        new_transactions = []

        for div in dividends:
            try:
                # Find or create asset
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=div["symbol"],
                    name=div["description"],
                    asset_class=div["asset_class"],
                    currency=div.get("currency", "USD"),
                    ibkr_symbol=div["original_symbol"],
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    db.query(Holding)
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
                    db.add(holding)
                    db.flush()  # Need ID for transaction FK

                # Compute content hash for deduplication
                content_hash = compute_transaction_hash(
                    external_txn_id=None,  # Dividends don't have external IDs in IBKR
                    txn_date=div["date"],
                    symbol=div["symbol"],
                    txn_type="Dividend",
                    quantity=div["amount"],  # Use amount as quantity for dividends
                    price=None,
                    fees=Decimal("0"),
                )

                # Check for existing transaction by hash
                existing = (
                    db.query(Transaction).filter(Transaction.content_hash == content_hash).first()
                )

                if existing:
                    if existing.broker_source_id != source_id:
                        existing.broker_source_id = source_id
                        stats["transferred"] += 1
                    else:
                        stats["skipped"] += 1
                    continue

                # Check for DRIP (Dividend Reinvestment Plan)
                # Look for Buy transaction on the same date
                same_day_buy = (
                    db.query(Transaction)
                    .filter(
                        Transaction.holding_id == holding.id,
                        Transaction.date == div["date"],
                        Transaction.type == "Buy",
                    )
                    .first()
                )

                # Build dividend notes
                dividend_notes = f"IBKR Import - Dividend ${div['amount']:.2f}"
                if same_day_buy:
                    dividend_notes += " [REINVESTED]"
                    logger.info(
                        f"Detected DRIP for {div['symbol']} on {div['date']}: ${div['amount']:.2f} → {same_day_buy.quantity} shares"
                    )

                # Create dividend transaction with amount field - add to batch list
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=div["date"],
                    type="Dividend",
                    quantity=None,
                    price_per_unit=None,
                    amount=div["amount"],  # Store in amount field
                    fees=Decimal("0"),
                    notes=dividend_notes,
                    content_hash=content_hash,
                )
                new_transactions.append(transaction)
                stats["imported"] += 1
                logger.debug(f"Created dividend for {div['symbol']}: ${div['amount']}")

            except Exception as e:
                logger.error(f"Error importing dividend {div.get('symbol')}: {str(e)}")
                stats["errors"].append(f"{div.get('symbol')}: {str(e)}")
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _import_transfers(
        db: Session, account_id: int, transfers: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import deposit/withdrawal transfers as transactions.

        Transfers affect cash balances but don't involve buying/selling assets.
        They're important for tracking capital contributions vs investment returns.

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            transfers: List of transfer dicts from parser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(transfers),
            "imported": 0,
            "duplicates_skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        # Collect new transactions for batch add
        new_transactions = []

        for transfer in transfers:
            try:
                currency = transfer["currency"]

                # Find or create cash asset for this currency
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=currency,
                    name=f"{currency} Cash",
                    asset_class="Cash",
                    currency=currency,
                    ibkr_symbol=currency,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create cash holding
                holding = (
                    db.query(Holding)
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
                    db.add(holding)
                    db.flush()  # Need ID for transaction FK

                # Check for duplicate
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.holding_id == holding.id,
                        Transaction.date == transfer["date"],
                        Transaction.type == transfer["type"],
                        Transaction.amount == transfer["amount"],
                    )
                    .first()
                )

                if existing:
                    stats["duplicates_skipped"] += 1
                    logger.debug(
                        f"Skipping duplicate {transfer['type']} for {currency} on {transfer['date']}"
                    )
                    continue

                # Create transfer transaction - add to batch list
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=transfer["date"],
                    type=transfer["type"],  # "Deposit" or "Withdrawal"
                    quantity=None,  # Transfers don't have quantity
                    price_per_unit=None,
                    amount=transfer["amount"],  # Use amount field for transfer value
                    fees=Decimal("0"),
                    notes=f"IBKR Import - {transfer['description']}",
                )
                new_transactions.append(transaction)
                stats["imported"] += 1
                logger.debug(f"Created {transfer['type']} for {currency}: {transfer['amount']}")

            except Exception as e:
                logger.error(f"Error importing transfer {transfer.get('type')}: {str(e)}")
                stats["errors"].append(f"{transfer.get('type')}: {str(e)}")
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _import_forex_transactions(
        db: Session, account_id: int, forex_txns: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import forex (currency conversion) transactions.

        Each forex conversion creates ONE transaction with:
        - holding_id: from_currency holding
        - to_holding_id: to_currency holding
        - amount: amount being converted (positive)
        - to_amount: amount received
        - exchange_rate: conversion rate

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            forex_txns: List of forex transaction dicts from parser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(forex_txns),
            "imported": 0,
            "duplicates_skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        # Collect new transactions for batch add
        new_transactions = []

        for forex in forex_txns:
            try:
                from_currency = forex["from_currency"]
                to_currency = forex["to_currency"]
                from_amount = forex["from_amount"]
                to_amount = forex["to_amount"]
                realized_pl = forex["realized_pl"]
                exchange_rate = to_amount / from_amount if from_amount > 0 else Decimal("0")

                # Find or create from_currency cash asset
                from_asset, from_created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=from_currency,
                    name=f"{from_currency} Cash",
                    asset_class="Cash",
                    currency=from_currency,
                    ibkr_symbol=from_currency,
                )

                if from_created:
                    stats["assets_created"] += 1

                # Find or create to_currency cash asset
                to_asset, to_created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=to_currency,
                    name=f"{to_currency} Cash",
                    asset_class="Cash",
                    currency=to_currency,
                    ibkr_symbol=to_currency,
                )

                if to_created:
                    stats["assets_created"] += 1

                # Find or create from_currency holding
                from_holding = (
                    db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == from_asset.id)
                    .first()
                )

                if not from_holding:
                    from_holding = Holding(
                        account_id=account_id,
                        asset_id=from_asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=True,
                    )
                    db.add(from_holding)
                    db.flush()  # Need ID for transaction FK

                # Find or create to_currency holding
                to_holding = (
                    db.query(Holding)
                    .filter(Holding.account_id == account_id, Holding.asset_id == to_asset.id)
                    .first()
                )

                if not to_holding:
                    to_holding = Holding(
                        account_id=account_id,
                        asset_id=to_asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=True,
                    )
                    db.add(to_holding)
                    db.flush()  # Need ID for transaction FK

                # Check for duplicate forex transaction (same date, currencies, amounts)
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.holding_id == from_holding.id,
                        Transaction.to_holding_id == to_holding.id,
                        Transaction.date == forex["date"],
                        Transaction.type == "Forex Conversion",
                        Transaction.amount == from_amount,
                    )
                    .first()
                )

                if existing:
                    stats["duplicates_skipped"] += 1
                    logger.debug(
                        f"Skipping duplicate forex conversion {from_currency}→{to_currency} on {forex['date']}"
                    )
                    continue

                # Create single forex transaction with all conversion details - add to batch list
                forex_txn = Transaction(
                    holding_id=from_holding.id,
                    broker_source_id=source_id,
                    to_holding_id=to_holding.id,
                    date=forex["date"],
                    type="Forex Conversion",
                    quantity=None,
                    price_per_unit=None,
                    amount=from_amount,  # Amount being converted (positive)
                    to_amount=to_amount,  # Amount received
                    exchange_rate=exchange_rate,
                    fees=Decimal("0"),
                    notes=f"IBKR Import - Convert {from_amount} {from_currency} to {to_amount} {to_currency} @ {exchange_rate:.4f} (P/L: {realized_pl})",
                )
                new_transactions.append(forex_txn)

                stats["imported"] += 1
                logger.debug(
                    f"Created forex conversion: {from_amount} {from_currency} → {to_amount} {to_currency}"
                )

            except Exception as e:
                logger.error(
                    f"Error importing forex transaction {forex.get('from_currency')}→{forex.get('to_currency')}: {str(e)}"
                )
                stats["errors"].append(
                    f"{forex.get('from_currency')}→{forex.get('to_currency')}: {str(e)}"
                )
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _import_other_cash_transactions(
        db: Session, account_id: int, cash_txns: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import other cash transactions (interest, tax, fees).

        These affect cash balances but aren't part of trades or forex.

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            cash_txns: List of cash transaction dicts from parser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(cash_txns),
            "imported": 0,
            "duplicates_skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        # Collect new transactions for batch add
        new_transactions = []

        for txn in cash_txns:
            try:
                currency = txn["currency"]
                txn_type = txn["type"]  # 'Interest', 'Tax', 'Fee'
                amount = txn["amount"]  # Keeps sign (negative for tax/fees)
                txn_date = txn["date"]
                description = txn.get("description", "")

                # Find or create cash asset for this currency
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=currency,
                    name=f"{currency} Cash",
                    asset_class="Cash",
                    currency=currency,
                    ibkr_symbol=currency,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create cash holding
                holding = (
                    db.query(Holding)
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
                    db.add(holding)
                    db.flush()  # Need ID for transaction FK

                # Check for duplicate
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.holding_id == holding.id,
                        Transaction.date == txn_date,
                        Transaction.type == txn_type,
                        Transaction.amount == amount,
                    )
                    .first()
                )

                if existing:
                    stats["duplicates_skipped"] += 1
                    logger.debug(f"Skipping duplicate {txn_type} for {currency} on {txn_date}")
                    continue

                # Create transaction - add to batch list
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=txn_date,
                    type=txn_type,
                    quantity=None,
                    price_per_unit=None,
                    amount=amount,
                    fees=Decimal("0"),
                    notes=f"IBKR Import - {description}",
                )
                new_transactions.append(transaction)
                stats["imported"] += 1
                logger.debug(f"Created {txn_type} for {currency}: {amount}")

            except Exception as e:
                logger.error(f"Error importing {txn.get('type')} transaction: {str(e)}")
                stats["errors"].append(f"{txn.get('type')}: {str(e)}")
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _import_dividend_cash(
        db: Session, account_id: int, dividends: list[dict], source_id: int | None = None
    ) -> dict:
        """
        Import dividend cash impact to the cash balance.

        Dividends credit cash in addition to being stored on the stock holding.
        This creates the cash-side entries.

        Uses batch operations to minimize database lock time.

        Args:
            db: Database session
            account_id: Our account ID
            dividends: List of dividend dicts from parser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(dividends),
            "imported": 0,
            "duplicates_skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        # Collect new transactions for batch add
        new_transactions = []

        for div in dividends:
            try:
                currency = div.get("currency", "USD")
                amount = div["amount"]
                div_date = div["date"]
                symbol = div.get("symbol", "unknown")

                # Find or create cash asset for this currency
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=currency,
                    name=f"{currency} Cash",
                    asset_class="Cash",
                    currency=currency,
                    ibkr_symbol=currency,
                )

                if created:
                    stats["assets_created"] += 1

                # Find or create cash holding
                holding = (
                    db.query(Holding)
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
                    db.add(holding)
                    db.flush()  # Need ID for transaction FK

                # Check for duplicate - use "Dividend Cash" type to distinguish from stock dividend
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.holding_id == holding.id,
                        Transaction.date == div_date,
                        Transaction.type == "Dividend Cash",
                        Transaction.amount == amount,
                    )
                    .first()
                )

                if existing:
                    stats["duplicates_skipped"] += 1
                    logger.debug(f"Skipping duplicate dividend cash for {currency} on {div_date}")
                    continue

                # Create cash dividend transaction - add to batch list
                transaction = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source_id,
                    date=div_date,
                    type="Dividend Cash",
                    quantity=None,
                    price_per_unit=None,
                    amount=amount,
                    fees=Decimal("0"),
                    notes=f"IBKR Import - Dividend from {symbol}",
                )
                new_transactions.append(transaction)
                stats["imported"] += 1
                logger.debug(f"Created dividend cash for {currency}: {amount} from {symbol}")

            except Exception as e:
                logger.error(f"Error importing dividend cash: {str(e)}")
                stats["errors"].append(f"dividend cash: {str(e)}")
                continue

        # Batch add all new transactions at once
        if new_transactions:
            db.add_all(new_transactions)
            db.flush()

        return stats

    @staticmethod
    def _find_or_create_asset(
        db: Session,
        symbol: str,
        name: str,
        asset_class: str,
        currency: str = "USD",
        ibkr_symbol: str = None,
        cusip: str = None,
        isin: str = None,
        conid: str = None,
        figi: str = None,
    ) -> tuple[Asset, bool]:
        """
        Find or auto-create asset.

        Args:
            db: Database session
            symbol: Yahoo Finance compatible symbol
            name: Asset name/description
            asset_class: Our asset class
            currency: Asset currency (USD, CAD, EUR, etc.)
            ibkr_symbol: Original IBKR symbol (if different)
            cusip: CUSIP identifier (permanent, doesn't change with ticker)
            isin: ISIN identifier (permanent, doesn't change with ticker)
            conid: IBKR contract ID (permanent)
            figi: Bloomberg Global ID (permanent)

        Returns:
            Tuple of (asset, created)
        """
        # Try to find existing asset
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()

        if asset:
            # Update currency if it was missing or different
            if asset.currency != currency:
                logger.info(f"Updating currency for {symbol}: {asset.currency} -> {currency}")
                asset.currency = currency

            # Update permanent identifiers if they're missing
            updated = False
            if cusip and not asset.cusip:
                asset.cusip = cusip
                updated = True
            if isin and not asset.isin:
                asset.isin = isin
                updated = True
            if conid and not asset.conid:
                asset.conid = conid
                updated = True
            if figi and not asset.figi:
                asset.figi = figi
                updated = True

            if updated:
                logger.debug(f"Updated identifiers for {symbol}")

            return (asset, False)

        # Asset doesn't exist, create it
        logger.info(f"Creating new asset: {symbol} ({name}) in {currency}")

        # Validate symbol with Yahoo Finance
        price_result = PriceFetcher.fetch_price(symbol)

        if not price_result:
            logger.warning(f"Symbol {symbol} not found in Yahoo Finance - creating anyway")

        # Try to fetch the real company name, category, and industry from Yahoo Finance
        # (only for non-Cash assets, and only if name looks like a symbol)
        resolved_name = name
        resolved_category = "Cash" if asset_class == "Cash" else None
        resolved_industry = None
        metadata_source = "ibkr"
        if asset_class != "Cash" and (name == symbol or not name or len(name) <= 10):
            metadata_result = AssetMetadataService.fetch_name_from_yfinance(symbol, asset_class)
            if metadata_result.name:
                resolved_name = metadata_result.name
                metadata_source = "yfinance"
            if metadata_result.category:
                resolved_category = metadata_result.category
            if metadata_result.industry:
                resolved_industry = metadata_result.industry
            if metadata_result.name or metadata_result.category or metadata_result.industry:
                logger.info(
                    f"Resolved metadata for {symbol}: name='{resolved_name}', "
                    f"category='{resolved_category}', industry='{resolved_industry}'"
                )

        asset = Asset(
            symbol=symbol,
            name=resolved_name,
            asset_class=asset_class,
            category=resolved_category,
            industry=resolved_industry,
            currency=currency,
            data_source="IBKR",
            last_fetched_price=price_result[0] if price_result else None,
            last_fetched_at=price_result[1] if price_result else None,
            is_manual_valuation=(price_result is None),
            # Permanent identifiers
            cusip=cusip,
            isin=isin,
            conid=conid,
            figi=figi,
        )

        # Store metadata (IBKR symbol if different, metadata source)
        meta_data = {"metadata_source": metadata_source}
        if ibkr_symbol and ibkr_symbol != symbol:
            meta_data["ibkr_symbol"] = ibkr_symbol
        asset.meta_data = meta_data

        db.add(asset)
        db.flush()

        logger.info(f"Created asset {symbol} with ID {asset.id}")
        return (asset, True)

    @staticmethod
    def _update_asset_prices(db: Session, symbols: list[str]) -> dict:
        """
        Fetch latest prices for imported symbols.

        Args:
            db: Database session
            symbols: List of symbols to update

        Returns:
            Statistics dictionary
        """
        stats = {"total": len(symbols), "updated": 0, "failed": 0}

        for symbol in symbols:
            try:
                asset = db.query(Asset).filter(Asset.symbol == symbol).first()
                if asset:
                    success = PriceFetcher.update_asset_price(db, asset)
                    if success:
                        stats["updated"] += 1
                    else:
                        stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error updating price for {symbol}: {str(e)}")
                stats["failed"] += 1
                continue

        return stats
