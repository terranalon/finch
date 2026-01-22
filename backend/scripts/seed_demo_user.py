"""Seed demo user for 'Demo Portfolio' feature."""

import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models.account import Account
from app.models.asset import Asset
from app.models.historical_snapshot import HistoricalSnapshot
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# USD to ILS exchange rate for historical data
USD_TO_ILS = Decimal("3.65")

DEMO_EMAIL = "demo@finch.com"
DEMO_PASSWORD = "Demo1234"  # Password for demo account (meets complexity requirements)

# Sample portfolio data - US stocks (popular stocks with realistic positions)
US_HOLDINGS_DATA = [
    # symbol, quantity, cost_basis_per_share, buy_date_offset_days
    ("MSFT", Decimal("25"), Decimal("380.50"), 180),  # Microsoft
    ("INTC", Decimal("100"), Decimal("32.25"), 90),   # Intel
    ("PANW", Decimal("15"), Decimal("175.00"), 120),  # Palo Alto Networks
    ("RIO", Decimal("50"), Decimal("65.40"), 60),     # Rio Tinto
    ("SLV", Decimal("200"), Decimal("22.15"), 150),   # iShares Silver Trust
    ("MARA", Decimal("75"), Decimal("18.50"), 45),    # MARA Holdings
    ("NU", Decimal("150"), Decimal("11.80"), 30),     # Nu Holdings
    ("FVRR", Decimal("30"), Decimal("28.50"), 75),    # Fiverr
]

# Israeli portfolio data - TASE stocks (Israel Stock Exchange)
# Note: These are common Israeli stocks - may need to be added to assets table
ISRAELI_HOLDINGS_DATA = [
    # symbol, quantity, cost_basis_per_share (ILS), buy_date_offset_days
    ("TEVA.TA", Decimal("500"), Decimal("58.50"), 120),   # Teva Pharmaceutical
    ("NICE.TA", Decimal("30"), Decimal("850.00"), 90),    # NICE Ltd
    ("LUMI.TA", Decimal("200"), Decimal("62.30"), 60),    # Bank Leumi
    ("POLI.TA", Decimal("150"), Decimal("45.20"), 45),    # Bank Hapoalim
]

# Keep backward compatibility alias
DEMO_HOLDINGS_DATA = US_HOLDINGS_DATA


def create_demo_user(db: DBSession) -> tuple[User, Portfolio, Portfolio | None]:
    """
    Create demo user with sample portfolios.

    Returns existing user if already created (idempotent).

    Returns:
        Tuple of (User, US Portfolio, Israeli Portfolio or None)
    """
    # Check if demo user already exists
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()

    if user:
        logger.info(f"Demo user already exists: {user.id}")
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
        us_portfolio = next((p for p in portfolios if "US" in p.name or "Demo" in p.name), portfolios[0] if portfolios else None)
        il_portfolio = next((p for p in portfolios if "Israeli" in p.name), None)
        return user, us_portfolio, il_portfolio

    # Create demo user
    user = User(
        email=DEMO_EMAIL,
        password_hash=AuthService.hash_password(DEMO_PASSWORD),
        is_active=True,
    )
    db.add(user)
    db.flush()  # Get user.id before creating portfolio

    # Create US Investments portfolio (default, USD)
    us_portfolio = Portfolio(
        user_id=user.id,
        name="US Investments",
        description="US stocks and ETFs",
        default_currency="USD",
        is_default=True,
    )
    db.add(us_portfolio)

    # Create Israeli Savings portfolio (ILS)
    il_portfolio = Portfolio(
        user_id=user.id,
        name="Israeli Savings",
        description="Israeli stocks and savings",
        default_currency="ILS",
        is_default=False,
    )
    db.add(il_portfolio)
    db.flush()

    logger.info(f"Created demo user: {user.email} with portfolios: {us_portfolio.name}, {il_portfolio.name}")
    return user, us_portfolio, il_portfolio


def seed_demo_data(db: DBSession) -> dict:
    """
    Seed complete demo data: user, portfolios, accounts, holdings, transactions.

    Returns:
        Dict with created objects and stats
    """
    # Create user and portfolios
    user, us_portfolio, il_portfolio = create_demo_user(db)

    # Check if demo data already seeded (has accounts)
    existing_accounts = db.query(Account).filter(Account.portfolio_id == us_portfolio.id).count()
    if existing_accounts > 0:
        logger.info("Demo data already seeded, skipping...")
        db.commit()
        return {
            "user": user,
            "us_portfolio": us_portfolio,
            "il_portfolio": il_portfolio,
            "status": "already_seeded",
        }

    # ============ US INVESTMENTS PORTFOLIO ============
    # Create US accounts
    brokerage_account = Account(
        portfolio_id=us_portfolio.id,
        name="Main Brokerage",
        institution="Interactive Brokers",
        account_type="brokerage",
        currency="USD",
        account_number="DU12345678",
        broker_type="ibkr",
        is_active=True,
    )
    db.add(brokerage_account)

    retirement_account = Account(
        portfolio_id=us_portfolio.id,
        name="Retirement IRA",
        institution="Fidelity",
        account_type="ira",
        currency="USD",
        account_number="Z99887766",
        broker_type=None,
        is_active=True,
    )
    db.add(retirement_account)
    db.flush()

    logger.info(f"Created US accounts: {brokerage_account.name}, {retirement_account.name}")

    # Get US assets by symbol
    assets_by_symbol: dict[str, Asset] = {}
    us_symbols = [h[0] for h in US_HOLDINGS_DATA]
    existing_assets = db.query(Asset).filter(Asset.symbol.in_(us_symbols)).all()
    for asset in existing_assets:
        assets_by_symbol[asset.symbol] = asset

    # Create US holdings and transactions
    holdings_created = 0
    transactions_created = 0
    today = date.today()

    for symbol, quantity, cost_per_share, days_ago in US_HOLDINGS_DATA:
        asset = assets_by_symbol.get(symbol)
        if not asset:
            logger.warning(f"Asset {symbol} not found in database, skipping...")
            continue

        # Distribute holdings between accounts (first 5 in brokerage, rest in retirement)
        account = brokerage_account if holdings_created < 5 else retirement_account
        cost_basis = quantity * cost_per_share

        holding = Holding(
            account_id=account.id,
            asset_id=asset.id,
            quantity=quantity,
            cost_basis=cost_basis,
            strategy_horizon="long_term",
            is_active=True,
        )
        db.add(holding)
        db.flush()
        holdings_created += 1

        # Create buy transaction
        buy_date = today - timedelta(days=days_ago)
        transaction = Transaction(
            holding_id=holding.id,
            date=buy_date,
            type="Buy",
            quantity=quantity,
            price_per_unit=cost_per_share,
            amount=cost_basis,
            fees=Decimal("1.00"),
            notes=f"Initial purchase of {symbol}",
        )
        db.add(transaction)
        transactions_created += 1

    # ============ ISRAELI SAVINGS PORTFOLIO ============
    il_accounts_created = 0
    if il_portfolio:
        # Create Israeli accounts
        leumi_account = Account(
            portfolio_id=il_portfolio.id,
            name="Bank Leumi Brokerage",
            institution="Bank Leumi",
            account_type="brokerage",
            currency="ILS",
            account_number="12-345-67890",
            broker_type=None,
            is_active=True,
        )
        db.add(leumi_account)

        pension_account = Account(
            portfolio_id=il_portfolio.id,
            name="Migdal Pension",
            institution="Migdal Insurance",
            account_type="pension",
            currency="ILS",
            account_number="PENS-2024-001",
            broker_type=None,
            is_active=True,
        )
        db.add(pension_account)
        db.flush()
        il_accounts_created = 2

        logger.info(f"Created Israeli accounts: {leumi_account.name}, {pension_account.name}")

        # Get Israeli assets by symbol (create if not exist)
        il_symbols = [h[0] for h in ISRAELI_HOLDINGS_DATA]
        il_existing_assets = db.query(Asset).filter(Asset.symbol.in_(il_symbols)).all()
        for asset in il_existing_assets:
            assets_by_symbol[asset.symbol] = asset

        # Create Israeli holdings and transactions
        for symbol, quantity, cost_per_share, days_ago in ISRAELI_HOLDINGS_DATA:
            asset = assets_by_symbol.get(symbol)
            if not asset:
                # Create the asset if it doesn't exist
                asset = Asset(
                    symbol=symbol,
                    name=symbol.replace(".TA", " (TASE)"),
                    asset_class="Equity",
                    currency="ILS",
                    exchange="TASE",
                )
                db.add(asset)
                db.flush()
                assets_by_symbol[symbol] = asset
                logger.info(f"Created Israeli asset: {symbol}")

            # Put holdings in Bank Leumi account
            cost_basis = quantity * cost_per_share

            holding = Holding(
                account_id=leumi_account.id,
                asset_id=asset.id,
                quantity=quantity,
                cost_basis=cost_basis,
                strategy_horizon="long_term",
                is_active=True,
            )
            db.add(holding)
            db.flush()
            holdings_created += 1

            # Create buy transaction
            buy_date = today - timedelta(days=days_ago)
            transaction = Transaction(
                holding_id=holding.id,
                date=buy_date,
                type="Buy",
                quantity=quantity,
                price_per_unit=cost_per_share,
                amount=cost_basis,
                fees=Decimal("5.00"),  # Israeli transaction fees tend to be higher
                notes=f"Purchase of {symbol} on TASE",
            )
            db.add(transaction)
            transactions_created += 1

    db.commit()
    logger.info(f"Created {holdings_created} holdings and {transactions_created} transactions")

    # Generate historical snapshots for the portfolio chart
    snapshots_created = seed_historical_snapshots(db, brokerage_account.id, retirement_account.id)

    # Generate historical snapshots for Israeli portfolio
    if il_portfolio and il_accounts_created > 0:
        il_snapshots = seed_historical_snapshots_ils(db, leumi_account.id, pension_account.id)
        snapshots_created += il_snapshots

    return {
        "user": user,
        "us_portfolio": us_portfolio,
        "il_portfolio": il_portfolio,
        "us_accounts": 2,
        "il_accounts": il_accounts_created,
        "holdings": holdings_created,
        "transactions": transactions_created,
        "snapshots": snapshots_created,
        "status": "created",
    }


def seed_historical_snapshots(
    db: DBSession,
    brokerage_account_id: int,
    retirement_account_id: int,
    days_back: int = 180,
) -> int:
    """
    Generate realistic historical snapshots for demo accounts.

    Creates daily portfolio value snapshots with:
    - Gradual growth trend (~15% annual)
    - Daily volatility (~1-2%)
    - Weekend gaps (no trading)

    Args:
        db: Database session
        brokerage_account_id: Main brokerage account ID
        retirement_account_id: Retirement account ID
        days_back: Number of days of history to generate

    Returns:
        Number of snapshots created
    """
    today = date.today()
    snapshots_created = 0

    # Starting values (work backwards from current approximate values)
    # Main brokerage: ~$39,000, Retirement: ~$4,300
    brokerage_current = Decimal("39500")
    retirement_current = Decimal("3800")

    # Calculate daily growth rate for ~15% annual return
    # (1.15)^(1/252) ≈ 1.00055 per trading day
    daily_growth = Decimal("1.00055")

    # Work backwards from today
    random.seed(42)  # Deterministic randomness for consistent demo data

    for days_ago in range(days_back, -1, -1):
        snapshot_date = today - timedelta(days=days_ago)

        # Skip weekends
        if snapshot_date.weekday() >= 5:
            continue

        # Calculate value for this historical date
        # More days ago = lower value (reverse the growth)
        trading_days_from_end = sum(
            1 for d in range(days_ago)
            if (today - timedelta(days=d)).weekday() < 5
        )

        # Base value with growth trend (earlier = lower)
        growth_factor = daily_growth ** trading_days_from_end
        brokerage_base = brokerage_current / growth_factor
        retirement_base = retirement_current / growth_factor

        # Add daily volatility (-2% to +2%)
        brokerage_volatility = Decimal(str(1 + random.uniform(-0.02, 0.02)))
        retirement_volatility = Decimal(str(1 + random.uniform(-0.02, 0.02)))

        brokerage_value = (brokerage_base * brokerage_volatility).quantize(Decimal("0.01"))
        retirement_value = (retirement_base * retirement_volatility).quantize(Decimal("0.01"))

        # Create snapshots for both accounts
        brokerage_snapshot = HistoricalSnapshot(
            date=snapshot_date,
            account_id=brokerage_account_id,
            total_value_usd=brokerage_value,
            total_value_ils=brokerage_value * USD_TO_ILS,
        )
        db.add(brokerage_snapshot)

        retirement_snapshot = HistoricalSnapshot(
            date=snapshot_date,
            account_id=retirement_account_id,
            total_value_usd=retirement_value,
            total_value_ils=retirement_value * USD_TO_ILS,
        )
        db.add(retirement_snapshot)

        snapshots_created += 2

    db.commit()
    logger.info(f"Created {snapshots_created} historical snapshots")
    return snapshots_created


def seed_historical_snapshots_ils(
    db: DBSession,
    leumi_account_id: int,
    pension_account_id: int,
    days_back: int = 180,
) -> int:
    """
    Generate realistic historical snapshots for Israeli demo accounts (ILS).

    Creates daily portfolio value snapshots with:
    - Gradual growth trend (~10% annual for Israeli market)
    - Daily volatility (~1.5%)
    - Weekend gaps (no trading)

    Args:
        db: Database session
        leumi_account_id: Bank Leumi brokerage account ID
        pension_account_id: Pension account ID
        days_back: Number of days of history to generate

    Returns:
        Number of snapshots created
    """
    today = date.today()
    snapshots_created = 0

    # Starting values in ILS (work backwards from current approximate values)
    # Based on holdings: TEVA 500*58.5 + NICE 30*850 + LUMI 200*62.3 + POLI 150*45.2 ≈ 74,000 ILS
    leumi_current = Decimal("74000")
    pension_current = Decimal("25000")  # Some pension savings

    # Calculate daily growth rate for ~10% annual return (Israeli market is a bit more conservative)
    # (1.10)^(1/252) ≈ 1.00038 per trading day
    daily_growth = Decimal("1.00038")

    # Work backwards from today
    random.seed(123)  # Different seed for variety

    for days_ago in range(days_back, -1, -1):
        snapshot_date = today - timedelta(days=days_ago)

        # Skip weekends (note: Israeli market is closed Fri-Sat, but we'll use same convention)
        if snapshot_date.weekday() >= 5:
            continue

        # Calculate value for this historical date
        trading_days_from_end = sum(
            1 for d in range(days_ago)
            if (today - timedelta(days=d)).weekday() < 5
        )

        # Base value with growth trend (earlier = lower)
        growth_factor = daily_growth ** trading_days_from_end
        leumi_base = leumi_current / growth_factor
        pension_base = pension_current / growth_factor

        # Add daily volatility (-1.5% to +1.5%)
        leumi_volatility = Decimal(str(1 + random.uniform(-0.015, 0.015)))
        pension_volatility = Decimal(str(1 + random.uniform(-0.015, 0.015)))

        leumi_value_ils = (leumi_base * leumi_volatility).quantize(Decimal("0.01"))
        pension_value_ils = (pension_base * pension_volatility).quantize(Decimal("0.01"))

        # Convert to USD for the snapshot (USD is used for portfolio charts)
        leumi_value_usd = (leumi_value_ils / USD_TO_ILS).quantize(Decimal("0.01"))
        pension_value_usd = (pension_value_ils / USD_TO_ILS).quantize(Decimal("0.01"))

        # Create snapshots for both accounts
        leumi_snapshot = HistoricalSnapshot(
            date=snapshot_date,
            account_id=leumi_account_id,
            total_value_usd=leumi_value_usd,
            total_value_ils=leumi_value_ils,
        )
        db.add(leumi_snapshot)

        pension_snapshot = HistoricalSnapshot(
            date=snapshot_date,
            account_id=pension_account_id,
            total_value_usd=pension_value_usd,
            total_value_ils=pension_value_ils,
        )
        db.add(pension_snapshot)

        snapshots_created += 2

    db.commit()
    logger.info(f"Created {snapshots_created} historical snapshots for Israeli accounts")
    return snapshots_created


def add_israeli_portfolio_to_existing_demo(db: DBSession) -> dict:
    """
    Add Israeli portfolio to existing demo user.

    Use this to add the Israeli portfolio without recreating the demo user.
    """
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not user:
        logger.error("Demo user not found")
        return {"status": "error", "message": "Demo user not found"}

    # Check if Israeli portfolio already exists
    il_portfolio = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.name == "Israeli Savings"
    ).first()

    if il_portfolio:
        logger.info("Israeli portfolio already exists")
        return {"status": "already_exists", "portfolio": il_portfolio}

    # Rename existing portfolio to "US Investments" if it's still "Demo Portfolio"
    us_portfolio = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    if us_portfolio and us_portfolio.name == "Demo Portfolio":
        us_portfolio.name = "US Investments"
        us_portfolio.description = "US stocks and ETFs"
        us_portfolio.is_default = True
        logger.info("Renamed Demo Portfolio to US Investments")

    # Create Israeli portfolio
    il_portfolio = Portfolio(
        user_id=user.id,
        name="Israeli Savings",
        description="Israeli stocks and savings",
        default_currency="ILS",
        is_default=False,
    )
    db.add(il_portfolio)
    db.flush()

    # Create Israeli accounts
    leumi_account = Account(
        portfolio_id=il_portfolio.id,
        name="Bank Leumi Brokerage",
        institution="Bank Leumi",
        account_type="brokerage",
        currency="ILS",
        account_number="12-345-67890",
        broker_type=None,
        is_active=True,
    )
    db.add(leumi_account)

    pension_account = Account(
        portfolio_id=il_portfolio.id,
        name="Migdal Pension",
        institution="Migdal Insurance",
        account_type="pension",
        currency="ILS",
        account_number="PENS-2024-001",
        broker_type=None,
        is_active=True,
    )
    db.add(pension_account)
    db.flush()

    # Get or create Israeli assets
    assets_by_symbol: dict[str, Asset] = {}
    il_symbols = [h[0] for h in ISRAELI_HOLDINGS_DATA]
    il_existing_assets = db.query(Asset).filter(Asset.symbol.in_(il_symbols)).all()
    for asset in il_existing_assets:
        assets_by_symbol[asset.symbol] = asset

    holdings_created = 0
    transactions_created = 0
    today = date.today()

    for symbol, quantity, cost_per_share, days_ago in ISRAELI_HOLDINGS_DATA:
        asset = assets_by_symbol.get(symbol)
        if not asset:
            # Create the asset if it doesn't exist
            asset = Asset(
                symbol=symbol,
                name=symbol.replace(".TA", " (TASE)"),
                asset_class="Equity",
                currency="ILS",
            )
            db.add(asset)
            db.flush()
            assets_by_symbol[symbol] = asset
            logger.info(f"Created Israeli asset: {symbol}")

        cost_basis = quantity * cost_per_share

        holding = Holding(
            account_id=leumi_account.id,
            asset_id=asset.id,
            quantity=quantity,
            cost_basis=cost_basis,
            strategy_horizon="long_term",
            is_active=True,
        )
        db.add(holding)
        db.flush()
        holdings_created += 1

        buy_date = today - timedelta(days=days_ago)
        transaction = Transaction(
            holding_id=holding.id,
            date=buy_date,
            type="Buy",
            quantity=quantity,
            price_per_unit=cost_per_share,
            amount=cost_basis,
            fees=Decimal("5.00"),
            notes=f"Purchase of {symbol} on TASE",
        )
        db.add(transaction)
        transactions_created += 1

    db.commit()
    logger.info(f"Created Israeli portfolio with {holdings_created} holdings")

    # Generate historical snapshots for Israeli portfolio
    snapshots_created = seed_historical_snapshots_ils(db, leumi_account.id, pension_account.id)

    return {
        "status": "created",
        "portfolio": il_portfolio,
        "accounts": 2,
        "holdings": holdings_created,
        "transactions": transactions_created,
        "snapshots": snapshots_created,
    }


def seed_historical_for_existing_demo(db: DBSession) -> int:
    """
    Add historical snapshots to existing demo accounts.

    Use this to add historical data without recreating the demo user.
    """
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not user:
        logger.error("Demo user not found")
        return 0

    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    accounts = db.query(Account).filter(Account.portfolio_id == portfolio.id).all()

    if len(accounts) < 2:
        logger.error("Expected 2 demo accounts")
        return 0

    # Clear existing snapshots for demo accounts
    for account in accounts:
        db.query(HistoricalSnapshot).filter(
            HistoricalSnapshot.account_id == account.id
        ).delete()
    db.commit()

    # Find brokerage and retirement accounts
    brokerage = next((a for a in accounts if "brokerage" in a.account_type.lower()), accounts[0])
    retirement = next((a for a in accounts if a.id != brokerage.id), accounts[1])

    return seed_historical_snapshots(db, brokerage.id, retirement.id)


def seed_historical_for_israeli_portfolio(db: DBSession) -> int:
    """
    Add historical snapshots to existing Israeli portfolio accounts.

    Use this to add historical data for the Israeli portfolio.
    """
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not user:
        logger.error("Demo user not found")
        return 0

    # Find Israeli portfolio
    il_portfolio = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.name == "Israeli Savings"
    ).first()

    if not il_portfolio:
        logger.error("Israeli Savings portfolio not found")
        return 0

    accounts = db.query(Account).filter(Account.portfolio_id == il_portfolio.id).all()

    if len(accounts) < 2:
        logger.error("Expected 2 Israeli accounts")
        return 0

    # Clear existing snapshots for Israeli accounts
    for account in accounts:
        db.query(HistoricalSnapshot).filter(
            HistoricalSnapshot.account_id == account.id
        ).delete()
    db.commit()

    # Find Leumi and pension accounts
    leumi = next((a for a in accounts if "Leumi" in a.name), accounts[0])
    pension = next((a for a in accounts if a.id != leumi.id), accounts[1])

    return seed_historical_snapshots_ils(db, leumi.id, pension.id)


if __name__ == "__main__":
    """Run as standalone script."""
    import sys

    logging.basicConfig(level=logging.INFO)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        if "--historical-only" in sys.argv:
            snapshots = seed_historical_for_existing_demo(db)
            print(f"\nHistorical data seeding complete: {snapshots} snapshots created")
        elif "--add-israeli" in sys.argv:
            result = add_israeli_portfolio_to_existing_demo(db)
            print("\nIsraeli portfolio addition complete:")
            print(f"  Status: {result['status']}")
            if result["status"] == "created":
                print(f"  Portfolio: {result['portfolio'].name}")
                print(f"  Accounts: {result['accounts']}")
                print(f"  Holdings: {result['holdings']}")
                print(f"  Transactions: {result['transactions']}")
                print(f"  Historical snapshots: {result.get('snapshots', 0)}")
        elif "--israeli-historical" in sys.argv:
            snapshots = seed_historical_for_israeli_portfolio(db)
            print(f"\nIsraeli historical data seeding complete: {snapshots} snapshots created")
        else:
            result = seed_demo_data(db)
            print("\nDemo data seeding complete:")
            print(f"  User: {result['user'].email}")
            print(f"  US Portfolio: {result['us_portfolio'].name}")
            if result.get('il_portfolio'):
                print(f"  Israeli Portfolio: {result['il_portfolio'].name}")
            print(f"  Status: {result['status']}")
            if result["status"] == "created":
                print(f"  US Accounts: {result['us_accounts']}")
                print(f"  Israeli Accounts: {result['il_accounts']}")
                print(f"  Holdings: {result['holdings']}")
                print(f"  Transactions: {result['transactions']}")
                print(f"  Historical snapshots: {result['snapshots']}")
    finally:
        db.close()
