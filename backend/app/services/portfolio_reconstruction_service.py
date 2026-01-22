"""Portfolio reconstruction service for historical performance tracking."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, CorporateAction, Holding, Transaction
from app.services.price_fetcher import PriceFetcher
from app.services.ticker_change_detection_service import TickerChangeDetectionService

logger = logging.getLogger(__name__)

# Currency codes for identifying forex pair assets (e.g., USD.CAD)
CURRENCY_CODES = frozenset(
    {"USD", "CAD", "ILS", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "SEK", "NOK", "DKK"}
)


def _is_forex_pair(symbol: str) -> bool:
    """Check if a symbol is a forex pair (e.g., USD.CAD)."""
    if "." not in symbol:
        return False
    parts = symbol.split(".")
    return len(parts) == 2 and parts[0] in CURRENCY_CODES and parts[1] in CURRENCY_CODES


def _resolve_quantity(txn: Transaction) -> Decimal | None:
    """Resolve quantity for deposits/withdrawals/transfers.

    Prefers quantity (8 decimal places for crypto) over amount (2 decimal places).
    """
    if txn.quantity is not None:
        return txn.quantity
    return txn.amount


class PortfolioReconstructionService:
    """
    Reconstruct portfolio holdings for any historical date by replaying transactions.

    This service enables accurate historical performance tracking by:
    1. Replaying all transactions chronologically up to a target date
    2. Tracking FIFO lots for accurate cost basis
    3. Handling all transaction types: Buy, Sell, Dividend, Forex Conversion, Transfer
    4. Supporting multi-currency portfolios
    """

    @staticmethod
    def reconstruct_holdings(
        db: Session, account_id: int, as_of_date: date, apply_ticker_changes: bool = True
    ) -> list[dict]:
        """
        Reconstruct portfolio holdings as they existed on a specific date.

        Algorithm:
        1. Get all transactions up to as_of_date (inclusive)
        2. Replay transactions in chronological order
        3. Track quantities using FIFO for stocks
        4. Track cash balances for each currency
        5. Return holdings as they existed on that date

        Args:
            db: Database session
            account_id: Account to reconstruct
            as_of_date: Target date for reconstruction
            apply_ticker_changes: If True, automatically merge holdings with matching
                                 permanent identifiers (CUSIP/ISIN/CONID). Enables
                                 automatic ticker symbol change detection.

        Returns:
            List of reconstructed holdings with quantities and cost basis
        """
        logger.info(f"Reconstructing portfolio for account {account_id} as of {as_of_date}")

        # Get all transactions up to the target date, ordered chronologically
        transactions = (
            db.query(Transaction, Holding, Asset)
            .join(Holding, Transaction.holding_id == Holding.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(Holding.account_id == account_id, Transaction.date <= as_of_date)
            .order_by(Transaction.date, Transaction.id)
            .all()
        )

        # Filter out forex pair assets (USD.CAD, USD.ILS, etc.)
        # These are IBKR synthetic tracking records, not real holdings
        filtered_transactions = []
        for txn, holding, asset in transactions:
            if _is_forex_pair(asset.symbol):
                logger.debug(f"Skipping forex pair asset: {asset.symbol}")
            else:
                filtered_transactions.append((txn, holding, asset))

        transactions = filtered_transactions
        logger.info(
            f"Found {len(transactions)} transactions to replay (after filtering forex pairs)"
        )

        # Initialize holdings map: {asset_id: HoldingState}
        holdings_map = {}

        # Replay each transaction
        for txn, holding, asset in transactions:
            if asset.id not in holdings_map:
                holdings_map[asset.id] = {
                    "asset": asset,
                    "quantity": Decimal("0"),
                    "cost_basis": Decimal("0"),
                    "lots": [],  # For FIFO tracking: [{qty, remaining, cost_per_unit, date}]
                }

            h = holdings_map[asset.id]

            # Process based on transaction type
            if txn.type == "Buy":
                # Add to position
                quantity = txn.quantity or Decimal("0")
                price = txn.price_per_unit or Decimal("0")
                fees = txn.fees or Decimal("0")

                h["quantity"] += quantity
                # Use amount if available, otherwise calculate from quantity * price
                if txn.amount is not None:
                    cost = txn.amount + fees
                else:
                    cost = (quantity * price) + fees
                h["cost_basis"] += cost

                # Track lot for FIFO
                h["lots"].append(
                    {
                        "quantity": quantity,
                        "remaining": quantity,
                        "cost_per_unit": price,
                        "fees": fees,
                        "date": txn.date,
                    }
                )

            elif txn.type == "Sell":
                # Reduce using FIFO
                # NOTE: Some brokers store sell quantity as negative, so use abs()
                quantity = abs(txn.quantity or Decimal("0"))
                h["quantity"] -= quantity
                remaining_to_sell = quantity

                for lot in h["lots"]:
                    if remaining_to_sell <= 0:
                        break

                    sold = min(lot["remaining"], remaining_to_sell)
                    lot["remaining"] -= sold

                    # Proportional cost basis reduction
                    cost_per_unit = lot.get("cost_per_unit") or Decimal("0")
                    cost_reduction = sold * cost_per_unit
                    lot_qty = lot.get("quantity") or Decimal("0")
                    lot_fees = lot.get("fees") or Decimal("0")
                    if lot_qty > 0:
                        fee_proportion = (sold / lot_qty) * lot_fees
                        cost_reduction += fee_proportion

                    h["cost_basis"] -= cost_reduction
                    remaining_to_sell -= sold

            elif txn.type == "Dividend":
                # Dividends are cash payments - they don't affect stock quantities.
                # For stock holdings, dividends are informational only (cash goes to cash balance).
                # DRIP (dividend reinvestment) appears as a separate "Buy" transaction.
                # Only add to quantity if this is actually a cash holding.
                if asset.asset_class == "Cash" and txn.amount is not None:
                    h["quantity"] += txn.amount
                    h["cost_basis"] += abs(txn.amount)
                    logger.debug(
                        f"Dividend received for {asset.symbol} on {txn.date}: ${txn.amount}"
                    )
                else:
                    logger.debug(
                        f"Skipping dividend for stock {asset.symbol} on {txn.date}: ${txn.amount} (cash payment, not shares)"
                    )

            elif txn.type == "Forex Conversion":
                # Forex conversions affect cash holdings (tracked in amount field)
                # NOTE: Forex conversions are internal movements - they don't change
                # total cost basis, just move value between currency holdings.
                if txn.amount is not None:
                    # Amount is positive for receiving currency, negative for sending
                    h["quantity"] += txn.amount

            elif txn.type == "Deposit":
                # Deposits add to holdings (prefer quantity for crypto precision)
                deposit_qty = _resolve_quantity(txn)
                if deposit_qty is not None:
                    h["quantity"] += deposit_qty

                    if asset.asset_class == "Cash":
                        # For cash deposits, cost_basis = amount deposited
                        h["cost_basis"] += abs(deposit_qty)
                    else:
                        # Crypto deposits: use price_per_unit if available
                        if txn.price_per_unit is not None:
                            cost = abs(deposit_qty) * txn.price_per_unit
                            h["cost_basis"] += cost
                            # Track FIFO lot for deposits with known cost
                            h["lots"].append(
                                {
                                    "quantity": abs(deposit_qty),
                                    "remaining": abs(deposit_qty),
                                    "cost_per_unit": txn.price_per_unit,
                                    "fees": Decimal("0"),
                                    "date": txn.date,
                                }
                            )

            elif txn.type == "Withdrawal":
                # Withdrawals subtract from holdings (prefer quantity for crypto precision)
                # Also subtract the fee if present (for crypto withdrawals, fee is in crypto units)
                withdrawal_qty = _resolve_quantity(txn)
                if withdrawal_qty is not None:
                    h["quantity"] -= abs(withdrawal_qty)
                    # Also subtract fee if present (crypto withdrawal fees)
                    if txn.fees and txn.fees > 0:
                        h["quantity"] -= txn.fees
                    # TODO: For crypto withdrawals, reduce cost_basis proportionally

            elif txn.type == "Trade Settlement":
                # Trade settlements record the cash impact of stock purchases/sales
                # Negative for purchases (cash decreases), positive for sales (cash increases)
                # NOTE: Trade settlements do NOT affect cost basis - they just move cash
                # for trades that happen within the account. Cost basis only changes
                # for actual deposits/withdrawals (external cash flows).
                if txn.amount is not None:
                    h["quantity"] += txn.amount

            elif txn.type == "Staking":
                # Staking rewards add to crypto holdings (unlike cash dividends)
                # The quantity field holds the number of tokens received
                if txn.quantity is not None:
                    h["quantity"] += txn.quantity
                    # Cost basis for staking rewards is typically 0 or fair market value at receipt
                    # For simplicity, we don't add to cost basis (tokens received for free)
                    logger.debug(
                        f"Staking reward for {asset.symbol} on {txn.date}: {txn.quantity} tokens"
                    )

            elif txn.type == "Transfer":
                # Internal transfers (e.g., Kraken staking auto-allocation)
                # Positive = receiving, negative = sending; no cost basis impact
                transfer_qty = _resolve_quantity(txn)
                if transfer_qty is not None:
                    h["quantity"] += transfer_qty
                    logger.debug(f"Transfer for {asset.symbol} on {txn.date}: {transfer_qty}")

            elif txn.type in ("Withdrawal Fee", "Custody Fee"):
                # Fees that reduce holdings (usually stored as negative quantities)
                fee_qty = _resolve_quantity(txn)
                if fee_qty is not None:
                    h["quantity"] += fee_qty  # fee_qty is already negative
                    logger.debug(f"{txn.type} for {asset.symbol} on {txn.date}: {fee_qty}")

            elif txn.type in ("Refund Fee", "Refund Withdrawal"):
                # Refunds that add back to holdings (usually stored as positive quantities)
                refund_qty = _resolve_quantity(txn)
                if refund_qty is not None:
                    h["quantity"] += refund_qty
                    logger.debug(f"{txn.type} for {asset.symbol} on {txn.date}: {refund_qty}")

            elif txn.type == "Interest":
                # Interest credits (usually on cash holdings like ILS)
                interest_qty = _resolve_quantity(txn)
                if interest_qty is not None:
                    h["quantity"] += interest_qty
                    if asset.asset_class == "Cash":
                        h["cost_basis"] += abs(interest_qty)
                    logger.debug(f"Interest for {asset.symbol} on {txn.date}: {interest_qty}")

        # CRITICAL: Replace transaction-calculated cash balances with authoritative StmtFunds data
        # This fixes the issue where transaction data may be incomplete or have missing forex conversions
        # Note: StmtFunds only has entries on dates with activity, so we forward-fill (use most recent balance)
        from sqlalchemy import func

        from app.models import DailyCashBalance

        try:
            # Get the most recent balance for each currency on or before as_of_date
            # This handles gaps in StmtFunds data (which only records activity dates)
            subquery = (
                db.query(
                    DailyCashBalance.currency, func.max(DailyCashBalance.date).label("max_date")
                )
                .filter(
                    DailyCashBalance.account_id == account_id, DailyCashBalance.date <= as_of_date
                )
                .group_by(DailyCashBalance.currency)
                .subquery()
            )

            latest_balances_query = (
                db.query(DailyCashBalance)
                .join(
                    subquery,
                    (DailyCashBalance.currency == subquery.c.currency)
                    & (DailyCashBalance.date == subquery.c.max_date),
                )
                .filter(DailyCashBalance.account_id == account_id)
                .all()
            )

            latest_balances = {balance.currency: balance for balance in latest_balances_query}

            # Apply StmtFunds balances to cash holdings (forward-filled)
            for asset_id, h in holdings_map.items():
                if h["asset"].asset_class == "Cash":
                    currency = h["asset"].symbol  # For cash, symbol = currency (USD, CAD, etc.)
                    if currency in latest_balances:
                        stmt_balance = latest_balances[currency].balance
                        balance_date = latest_balances[currency].date
                        logger.debug(
                            f"Using StmtFunds for {currency} on {as_of_date}: "
                            f"{stmt_balance:.2f} (from {balance_date}, was {h['quantity']:.2f} from txns)"
                        )
                        h["quantity"] = stmt_balance
                        h["cost_basis"] = abs(stmt_balance)  # For cash, cost_basis = amount
                    else:
                        logger.warning(
                            f"No StmtFunds data found for {currency} up to {as_of_date}, "
                            f"using transaction-calculated value: {h['quantity']:.2f}"
                        )
        except Exception as e:
            logger.warning(
                f"Could not load StmtFunds balances for {as_of_date}: {e}. "
                f"Falling back to transaction-calculated cash balances."
            )

        # Filter to non-zero holdings and format output
        reconstructed = []
        for asset_id, h in holdings_map.items():
            if h["quantity"] != 0:  # Only include active holdings
                reconstructed.append(
                    {
                        "asset_id": asset_id,
                        "symbol": h["asset"].symbol,
                        "name": h["asset"].name,
                        "asset_class": h["asset"].asset_class,
                        "currency": h["asset"].currency,
                        "quantity": h["quantity"],
                        "cost_basis": h["cost_basis"],
                        "lots": [
                            lot for lot in h["lots"] if lot["remaining"] > 0
                        ],  # Active lots only
                    }
                )

        logger.info(f"Reconstructed {len(reconstructed)} non-zero holdings for {as_of_date}")

        # Apply corporate actions (both manual and automatic)
        if apply_ticker_changes:
            # Step 1: Apply manual corporate actions from database
            reconstructed = PortfolioReconstructionService._apply_manual_corporate_actions(
                db, reconstructed, as_of_date
            )

            # Step 2: Apply automatic ticker symbol change detection (for simple rebrands)
            merged_holdings, applied_changes = (
                TickerChangeDetectionService.apply_ticker_changes_to_reconstruction(
                    db, reconstructed
                )
            )

            if applied_changes:
                logger.info(f"Applied {len(applied_changes)} automatic ticker changes:")
                for change in applied_changes:
                    logger.info(
                        f"  {change['from_symbol']} -> {change['to_symbol']} "
                        f"({change['quantity_merged']} shares merged)"
                    )
                reconstructed = merged_holdings

        return reconstructed

    @staticmethod
    def _apply_manual_corporate_actions(
        db: Session, reconstructed_holdings: list[dict], as_of_date: date
    ) -> list[dict]:
        """
        Apply manual corporate actions from database.

        This handles cases where identifiers changed (SPAC mergers, etc.) that
        automatic detection can't catch.

        Args:
            db: Database session
            reconstructed_holdings: Holdings from reconstruction
            as_of_date: Reconstruction date

        Returns:
            Holdings with manual corporate actions applied
        """
        # Get all corporate actions that are effective on or before the reconstruction date
        actions = (
            db.query(CorporateAction).filter(CorporateAction.effective_date <= as_of_date).all()
        )

        if not actions:
            return reconstructed_holdings

        logger.info(f"Applying {len(actions)} manual corporate actions")

        # Build merge map: old_asset_id -> new_asset_id
        merge_map = {}
        for action in actions:
            if action.new_asset_id:
                merge_map[action.old_asset_id] = action.new_asset_id
                logger.debug(
                    f"Corporate action: {action.action_type} - "
                    f"Asset {action.old_asset_id} -> {action.new_asset_id}"
                )

        # Apply merges
        merged_holdings = {}

        for holding in reconstructed_holdings:
            asset_id = holding["asset_id"]

            if asset_id in merge_map:
                # This asset has a corporate action
                new_asset_id = merge_map[asset_id]
                old_asset = db.query(Asset).get(asset_id)
                new_asset = db.query(Asset).get(new_asset_id)

                logger.info(
                    f"Merging {old_asset.symbol} ({holding['quantity']} shares) "
                    f"into {new_asset.symbol} due to corporate action"
                )

                # Merge into new asset
                if new_asset_id in merged_holdings:
                    merged_holdings[new_asset_id]["quantity"] += holding["quantity"]
                    merged_holdings[new_asset_id]["cost_basis"] += holding["cost_basis"]
                else:
                    merged_holdings[new_asset_id] = {
                        **holding,
                        "asset_id": new_asset_id,
                        "symbol": new_asset.symbol,
                        "name": new_asset.name,
                        "quantity": holding["quantity"],
                        "cost_basis": holding["cost_basis"],
                    }
            else:
                # No corporate action for this asset
                if asset_id in merged_holdings:
                    merged_holdings[asset_id]["quantity"] += holding["quantity"]
                    merged_holdings[asset_id]["cost_basis"] += holding["cost_basis"]
                else:
                    merged_holdings[asset_id] = holding

        return list(merged_holdings.values())

    @staticmethod
    def calculate_portfolio_value(
        db: Session, account_id: int, as_of_date: date, target_currency: str = "USD"
    ) -> dict:
        """
        Calculate total portfolio value for a specific date using reconstruction.

        Args:
            db: Database session
            account_id: Account to value
            as_of_date: Target date
            target_currency: Currency for valuation (default: USD)

        Returns:
            Dictionary with portfolio value breakdown
        """
        holdings = PortfolioReconstructionService.reconstruct_holdings(db, account_id, as_of_date)

        total_value = Decimal("0")
        holdings_detail = []

        for holding in holdings:
            # Get price as of target date (or closest available)
            asset = db.query(Asset).get(holding["asset_id"])

            # For cash assets, price is always 1.0 in their own currency
            if asset.asset_class == "Cash":
                price = Decimal("1.0")
            else:
                # Fetch historical price (this would need enhancement to fetch historical data)
                # For now, use current price as approximation
                price_data = PriceFetcher.fetch_price(asset.symbol)
                price = Decimal(str(price_data[0])) if price_data else None

            if not price:
                logger.warning(f"No price available for {asset.symbol} on {as_of_date}")
                continue

            # Calculate value in asset's native currency
            value_native = holding["quantity"] * price

            # Convert to target currency if needed
            if asset.currency != target_currency:
                # TODO: Implement historical exchange rate lookup
                # For now, use simplified conversion (needs enhancement)
                value = value_native  # Placeholder
            else:
                value = value_native

            total_value += value

            holdings_detail.append(
                {
                    "symbol": holding["symbol"],
                    "quantity": float(holding["quantity"]),
                    "price": float(price),
                    "value": float(value),
                    "currency": asset.currency,
                    "cost_basis": float(holding["cost_basis"]),
                }
            )

        return {
            "date": as_of_date.isoformat(),
            "account_id": account_id,
            "total_value": float(total_value),
            "currency": target_currency,
            "holdings": holdings_detail,
            "holding_count": len(holdings_detail),
        }

    @staticmethod
    def validate_reconstruction(db: Session, account_id: int, as_of_date: date = None) -> dict:
        """
        Validate reconstruction accuracy by comparing with current holdings.

        Args:
            db: Database session
            account_id: Account to validate
            as_of_date: Date to reconstruct (defaults to today)

        Returns:
            Validation results with discrepancies
        """
        if not as_of_date:
            as_of_date = date.today()

        # Get current holdings from database
        current_holdings = (
            db.query(Holding, Asset)
            .join(Asset)
            .filter(Holding.account_id == account_id, Holding.quantity != 0)
            .all()
        )

        # Filter out forex pair assets from current holdings
        filtered_current = []
        for holding, asset in current_holdings:
            if _is_forex_pair(asset.symbol):
                logger.debug(f"Skipping forex pair asset from validation: {asset.symbol}")
            else:
                filtered_current.append((holding, asset))

        current_holdings = filtered_current

        # Get reconstructed holdings (already filtered in reconstruct_holdings)
        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, as_of_date
        )

        # Build lookup maps
        current_map = {holding.asset_id: holding for holding, asset in current_holdings}
        reconstructed_map = {h["asset_id"]: h for h in reconstructed}

        # Compare
        discrepancies = []
        all_asset_ids = set(current_map.keys()) | set(reconstructed_map.keys())

        for asset_id in all_asset_ids:
            current = current_map.get(asset_id)
            recon = reconstructed_map.get(asset_id)

            current_qty = current.quantity if current else Decimal("0")
            recon_qty = recon["quantity"] if recon else Decimal("0")

            diff = abs(current_qty - recon_qty)

            # Allow small rounding differences (0.0001 shares)
            if diff > Decimal("0.0001"):
                asset = db.query(Asset).get(asset_id)
                discrepancies.append(
                    {
                        "asset_id": asset_id,
                        "symbol": asset.symbol,
                        "current_quantity": float(current_qty),
                        "reconstructed_quantity": float(recon_qty),
                        "difference": float(diff),
                    }
                )

        return {
            "is_valid": len(discrepancies) == 0,
            "date": as_of_date.isoformat(),
            "total_holdings_current": len(current_map),
            "total_holdings_reconstructed": len(reconstructed_map),
            "discrepancies": discrepancies,
        }
