"""Historical snapshot service for portfolio tracking."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Account, HistoricalSnapshot
from app.services.currency_service import CurrencyService
from app.services.historical_data_fetcher import HistoricalDataFetcher
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.price_fetcher import PriceFetcher

logger = logging.getLogger(__name__)


def update_snapshot_status(db: Session, account_id: int, status: str | None) -> None:
    """Update the snapshot_status field for an account.

    Args:
        db: Database session
        account_id: Account to update
        status: New status value ('generating', 'ready', 'failed', or None to clear)
    """
    account = db.get(Account, account_id)
    if account:
        account.snapshot_status = status
        db.commit()


def generate_snapshots_background(account_id: int, start_date: date) -> None:
    """Background task to generate historical snapshots after import.

    This function runs in a separate thread/task after the HTTP response
    has been sent. It generates historical snapshots for the account
    from the start_date to today.

    Args:
        account_id: Account to generate snapshots for
        start_date: Earliest date from the imported data
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        SnapshotService.generate_account_snapshots(
            db, account_id, start_date, date.today(), invalidate_existing=True
        )
        update_snapshot_status(db, account_id, "ready")
        logger.info("Background snapshot generation complete for account %d", account_id)
    except Exception:
        logger.exception("Background snapshot generation failed for account %d", account_id)
        update_snapshot_status(db, account_id, "failed")
    finally:
        db.close()


class SnapshotService:
    """Service for creating and managing portfolio snapshots."""

    @staticmethod
    def create_portfolio_snapshot(
        db: Session,
        snapshot_date: date | None = None,
        allowed_account_ids: list[int] | None = None,
    ) -> dict:
        """
        Create a snapshot of the entire portfolio or specific accounts.

        Args:
            db: Database session
            snapshot_date: Date for the snapshot (defaults to today)
            allowed_account_ids: List of account IDs to snapshot (defaults to all)

        Returns:
            Dictionary with snapshot statistics
        """
        if not snapshot_date:
            snapshot_date = date.today()

        stats = {
            "date": snapshot_date.isoformat(),
            "snapshots_created": 0,
            "total_value_usd": Decimal("0"),
            "accounts": [],
        }

        # Get accounts (optionally filtered)
        query = select(Account)
        if allowed_account_ids is not None:
            query = query.where(Account.id.in_(allowed_account_ids))

        accounts = db.execute(query).scalars().all()

        for account in accounts:
            snapshot_data = SnapshotService._create_account_snapshot(db, account, snapshot_date)

            if snapshot_data:
                stats["snapshots_created"] += 1
                stats["total_value_usd"] += snapshot_data["value_usd"]
                stats["accounts"].append(
                    {
                        "account_id": account.id,
                        "account_name": account.name,
                        "value_usd": float(snapshot_data["value_usd"]),
                    }
                )

        logger.info(f"Created {stats['snapshots_created']} snapshots for {snapshot_date}")
        return stats

    @staticmethod
    def _create_account_snapshot(db: Session, account: Account, snapshot_date: date) -> dict | None:
        """
        Create a snapshot for a single account using transaction reconstruction.

        Args:
            db: Database session
            account: Account model instance
            snapshot_date: Date for the snapshot

        Returns:
            Dictionary with snapshot data or None if no holdings
        """
        # Check if snapshot already exists for this account and date
        existing = db.execute(
            select(HistoricalSnapshot).where(
                and_(
                    HistoricalSnapshot.account_id == account.id,
                    HistoricalSnapshot.date == snapshot_date,
                )
            )
        ).scalar_one_or_none()

        if existing:
            logger.info(f"Snapshot already exists for account {account.name} on {snapshot_date}")
            return None

        # Use transaction reconstruction for accurate holdings
        from app.services.portfolio_reconstruction_service import PortfolioReconstructionService

        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account.id, snapshot_date, apply_ticker_changes=True
        )

        if not reconstructed:
            logger.debug(f"No holdings for account {account.name} on {snapshot_date}")
            return None

        total_value_usd = Decimal("0")

        for holding in reconstructed:
            asset_id = holding["asset_id"]
            quantity = holding["quantity"]
            currency = holding["currency"]
            asset_class = holding.get("asset_class", "")
            symbol = holding["symbol"]

            # Handle cash differently - skip negative balances (liabilities)
            if asset_class == "Cash":
                if quantity <= 0:
                    logger.debug(
                        f"Skipping negative cash balance: {symbol} "
                        f"{float(quantity):,.2f} (liability, not asset)"
                    )
                    continue

                # For positive cash, value is simply the amount
                # Convert to USD if needed
                if currency != "USD":
                    rate_to_usd = CurrencyService.get_exchange_rate(
                        db, currency, "USD", snapshot_date
                    )
                    if rate_to_usd:
                        total_value_usd += quantity * rate_to_usd
                    else:
                        logger.warning(
                            f"No {currency}/USD rate for {snapshot_date}, "
                            f"using native value for cash {symbol}"
                        )
                        total_value_usd += quantity
                else:
                    total_value_usd += quantity

                continue

            # For stocks/other assets, get price and calculate value
            price = PriceFetcher.get_price_for_date(db, asset_id, snapshot_date)

            if not price or price <= 0:
                logger.warning(
                    f"Skipping {symbol} in account {account.name} - no price available for {snapshot_date}"
                )
                continue

            # Calculate market value in asset's native currency
            market_value_native = quantity * price

            # Convert to USD using historical exchange rate for snapshot date
            if currency != "USD":
                rate_to_usd = CurrencyService.get_exchange_rate(db, currency, "USD", snapshot_date)
                if rate_to_usd:
                    market_value_usd = market_value_native * rate_to_usd
                else:
                    logger.warning(
                        f"No exchange rate for {currency}/USD on {snapshot_date}, "
                        f"using native value"
                    )
                    market_value_usd = market_value_native
            else:
                market_value_usd = market_value_native

            total_value_usd += market_value_usd

        # Convert total USD value to ILS using historical exchange rate
        usd_to_ils_rate = CurrencyService.get_exchange_rate(db, "USD", "ILS", snapshot_date)

        if usd_to_ils_rate:
            total_value_ils = total_value_usd * usd_to_ils_rate
        else:
            logger.warning(f"No USD/ILS exchange rate for {snapshot_date}, using USD value")
            total_value_ils = total_value_usd

        # Create the snapshot
        snapshot = HistoricalSnapshot(
            account_id=account.id,
            date=snapshot_date,
            total_value_usd=total_value_usd,
            total_value_ils=total_value_ils,
        )

        db.add(snapshot)
        db.commit()

        logger.info(
            f"Created snapshot for account {account.name}: "
            f"${total_value_usd:.2f} USD / ₪{total_value_ils:.2f} ILS"
        )

        return {
            "account_id": account.id,
            "date": snapshot_date,
            "value_usd": total_value_usd,
            "value_ils": total_value_ils,
        }

    @staticmethod
    def get_account_history(
        db: Session,
        account_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
    ) -> list[dict]:
        """
        Get historical snapshots for an account.

        Args:
            db: Database session
            account_id: Account ID
            start_date: Start date for history
            end_date: End date for history
            limit: Maximum number of snapshots to return

        Returns:
            List of snapshot dictionaries
        """
        query = select(HistoricalSnapshot).where(HistoricalSnapshot.account_id == account_id)

        if start_date:
            query = query.where(HistoricalSnapshot.date >= start_date)

        if end_date:
            query = query.where(HistoricalSnapshot.date <= end_date)

        query = query.order_by(HistoricalSnapshot.date.desc()).limit(limit)

        snapshots = db.execute(query).scalars().all()

        return [
            {
                "date": snapshot.date.isoformat(),
                "value_usd": float(snapshot.total_value_usd) if snapshot.total_value_usd else 0,
                "value_ils": float(snapshot.total_value_ils) if snapshot.total_value_ils else 0,
            }
            for snapshot in snapshots
        ]

    @staticmethod
    def get_portfolio_history(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
        allowed_account_ids: list[int] | None = None,
    ) -> list[dict]:
        """
        Get aggregated portfolio history across all accounts.

        Args:
            db: Database session
            start_date: Start date for history
            end_date: End date for history
            limit: Maximum number of data points
            allowed_account_ids: List of account IDs to include (for multi-tenant filtering)

        Returns:
            List of aggregated snapshot dictionaries
        """
        # Build query with joins
        query = select(
            HistoricalSnapshot.date,
            func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"),
            func.sum(HistoricalSnapshot.total_value_ils).label("total_ils"),
        ).join(Account, HistoricalSnapshot.account_id == Account.id)

        # Multi-tenant filter by allowed account IDs
        if allowed_account_ids is not None:
            query = query.where(HistoricalSnapshot.account_id.in_(allowed_account_ids))

        if start_date:
            query = query.where(HistoricalSnapshot.date >= start_date)

        if end_date:
            query = query.where(HistoricalSnapshot.date <= end_date)

        query = query.group_by(HistoricalSnapshot.date)
        query = query.order_by(HistoricalSnapshot.date.desc())
        query = query.limit(limit)

        results = db.execute(query).all()

        return [
            {
                "date": row.date.isoformat(),
                "value_usd": float(row.total_usd),
                "value_ils": float(row.total_ils),
            }
            for row in results
        ]

    @staticmethod
    def backfill_historical_snapshots(
        db: Session, account_id: int, start_date: date, end_date: date
    ) -> dict:
        """
        Backfill historical snapshots using transaction reconstruction.

        This method generates portfolio snapshots for every day between start_date and end_date
        by reconstructing holdings from transaction history. This is useful for:
        - Generating historical performance charts
        - Filling gaps in snapshot data
        - Creating snapshots retroactively before automated collection started

        Args:
            db: Database session
            account_id: Account to backfill
            start_date: First date to generate snapshots for
            end_date: Last date to generate snapshots for

        Returns:
            Dictionary with backfill statistics
        """
        from datetime import timedelta

        account = db.execute(select(Account).where(Account.id == account_id)).scalar_one_or_none()

        if not account:
            raise ValueError(f"Account {account_id} not found")

        logger.info(
            f"Starting backfill for account {account.name} ({account_id}) "
            f"from {start_date} to {end_date}"
        )

        stats = {
            "account_id": account_id,
            "account_name": account.name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": (end_date - start_date).days + 1,
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        current_date = start_date

        while current_date <= end_date:
            try:
                # Check if snapshot already exists
                existing = db.execute(
                    select(HistoricalSnapshot).where(
                        and_(
                            HistoricalSnapshot.account_id == account_id,
                            HistoricalSnapshot.date == current_date,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    logger.debug(f"Snapshot already exists for {current_date}, skipping")
                    stats["skipped"] += 1
                    current_date += timedelta(days=1)
                    continue

                # Reconstruct holdings for this date
                reconstructed = PortfolioReconstructionService.reconstruct_holdings(
                    db, account_id, current_date, apply_ticker_changes=True
                )

                if not reconstructed:
                    logger.debug(f"No holdings for {current_date}, skipping")
                    stats["skipped"] += 1
                    current_date += timedelta(days=1)
                    continue

                # Calculate total portfolio value
                total_value_usd = Decimal("0")

                for holding in reconstructed:
                    asset_id = holding["asset_id"]
                    quantity = holding["quantity"]
                    currency = holding["currency"]
                    asset_class = holding.get("asset_class", "")

                    # Handle cash differently - skip negative balances as they represent liabilities
                    if asset_class == "Cash":
                        if quantity <= 0:
                            logger.debug(
                                f"Skipping negative cash balance: {holding['symbol']} "
                                f"{float(quantity):,.2f} (liability, not asset)"
                            )
                            continue

                        # For positive cash, value is simply the amount
                        # Convert to USD if needed
                        if currency != "USD":
                            rate_to_usd = CurrencyService.get_exchange_rate(
                                db, currency, "USD", current_date
                            )
                            if rate_to_usd:
                                total_value_usd += quantity * rate_to_usd
                            else:
                                logger.warning(
                                    f"No {currency}/USD rate for {current_date}, "
                                    f"using native value for cash {holding['symbol']}"
                                )
                                total_value_usd += quantity
                        else:
                            total_value_usd += quantity

                        continue

                    # For stocks/other assets, get price and calculate value
                    price = PriceFetcher.get_price_for_date(db, asset_id, current_date)

                    if not price or price <= 0:
                        logger.warning(
                            f"No price for {holding['symbol']} on {current_date}, skipping this asset"
                        )
                        continue

                    # Calculate market value in native currency
                    market_value_native = quantity * price

                    # Convert to USD
                    if currency != "USD":
                        rate_to_usd = CurrencyService.get_exchange_rate(
                            db, currency, "USD", current_date
                        )
                        if rate_to_usd:
                            market_value_usd = market_value_native * rate_to_usd
                        else:
                            logger.warning(
                                f"No {currency}/USD rate for {current_date}, "
                                f"using native value for {holding['symbol']}"
                            )
                            market_value_usd = market_value_native
                    else:
                        market_value_usd = market_value_native

                    total_value_usd += market_value_usd

                # Convert to ILS
                usd_to_ils_rate = CurrencyService.get_exchange_rate(db, "USD", "ILS", current_date)
                if usd_to_ils_rate:
                    total_value_ils = total_value_usd * usd_to_ils_rate
                else:
                    logger.warning(f"No USD/ILS rate for {current_date}, using USD value")
                    total_value_ils = total_value_usd

                # Create the snapshot
                snapshot = HistoricalSnapshot(
                    account_id=account_id,
                    date=current_date,
                    total_value_usd=total_value_usd,
                    total_value_ils=total_value_ils,
                )

                db.add(snapshot)
                db.commit()

                stats["created"] += 1
                logger.info(
                    f"Created snapshot for {current_date}: "
                    f"${total_value_usd:.2f} USD (progress: {stats['created']}/{stats['total_days']})"
                )

            except Exception as e:
                error_msg = f"Error creating snapshot for {current_date}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append({"date": current_date.isoformat(), "error": str(e)})
                db.rollback()

            current_date += timedelta(days=1)

        logger.info(
            f"Backfill completed: {stats['created']} created, "
            f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
        )

        return stats

    @staticmethod
    def generate_account_snapshots(
        db: Session,
        account_id: int,
        start_date: date,
        end_date: date,
        invalidate_existing: bool = False,
    ) -> dict:
        """
        Generate historical snapshots using streaming reconstruction.

        This is the unified entry point for snapshot generation, used by both
        background import tasks and the daily DAG.

        Args:
            db: Database session
            account_id: Account to generate snapshots for
            start_date: First date to generate
            end_date: Last date to generate
            invalidate_existing: If True, delete existing snapshots in range first

        Returns:
            Stats dict with created, skipped, errors counts
        """
        stats = {
            "account_id": account_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        # Optionally delete existing snapshots
        if invalidate_existing:
            deleted = (
                db.query(HistoricalSnapshot)
                .filter(
                    HistoricalSnapshot.account_id == account_id,
                    HistoricalSnapshot.date >= start_date,
                    HistoricalSnapshot.date <= end_date,
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info(f"Deleted {deleted} existing snapshots for account {account_id}")

        # Ensure historical data exists
        try:
            HistoricalDataFetcher.ensure_historical_data(db, account_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            stats["errors"].append(f"Historical data fetch failed: {e}")

        # Stream through reconstruction and create snapshots
        for snapshot_date, holdings in PortfolioReconstructionService.reconstruct_holdings_timeline(
            db, account_id, start_date, end_date
        ):
            try:
                # Check if snapshot already exists
                existing = db.execute(
                    select(HistoricalSnapshot).where(
                        and_(
                            HistoricalSnapshot.account_id == account_id,
                            HistoricalSnapshot.date == snapshot_date,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    stats["skipped"] += 1
                    continue

                # Value holdings
                total_usd, total_ils = SnapshotService._value_holdings(db, holdings, snapshot_date)

                # Create snapshot
                snapshot = HistoricalSnapshot(
                    account_id=account_id,
                    date=snapshot_date,
                    total_value_usd=total_usd,
                    total_value_ils=total_ils,
                )
                db.add(snapshot)
                stats["created"] += 1

                # Commit in batches of 100
                if stats["created"] % 100 == 0:
                    db.commit()
                    logger.info(f"Generated {stats['created']} snapshots...")

            except Exception as e:
                logger.error(f"Error creating snapshot for {snapshot_date}: {e}")
                stats["errors"].append(f"{snapshot_date}: {e}")

        # Final commit
        db.commit()
        logger.info(
            f"Snapshot generation complete: {stats['created']} created, "
            f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
        )

        return stats

    @staticmethod
    def _value_holdings(
        db: Session,
        holdings: list[dict],
        snapshot_date: date,
    ) -> tuple[Decimal, Decimal]:
        """
        Value holdings and return total in USD and ILS.

        Args:
            db: Database session
            holdings: List of holding dicts with quantity, currency, asset_class, etc.
            snapshot_date: Date for price/rate lookups

        Returns:
            Tuple of (total_value_usd, total_value_ils)
        """
        total_value_usd = Decimal("0")

        for holding in holdings:
            quantity = holding["quantity"]
            currency = holding["currency"]
            asset_class = holding.get("asset_class", "")
            asset_id = holding.get("asset_id")

            # Handle cash
            if asset_class == "Cash":
                if quantity <= 0:
                    continue
                if currency != "USD":
                    rate = CurrencyService.get_exchange_rate(db, currency, "USD", snapshot_date)
                    if rate:
                        total_value_usd += quantity * rate
                    else:
                        total_value_usd += quantity
                else:
                    total_value_usd += quantity
                continue

            # Get price for non-cash
            price = PriceFetcher.get_price_for_date(db, asset_id, snapshot_date)
            if not price or price <= 0:
                continue

            market_value = quantity * price

            # Convert to USD
            if currency != "USD":
                rate = CurrencyService.get_exchange_rate(db, currency, "USD", snapshot_date)
                if rate:
                    market_value = market_value * rate

            total_value_usd += market_value

        # Convert to ILS
        usd_ils_rate = CurrencyService.get_exchange_rate(db, "USD", "ILS", snapshot_date)
        if usd_ils_rate:
            total_value_ils = total_value_usd * usd_ils_rate
        else:
            total_value_ils = total_value_usd

        return total_value_usd, total_value_ils
