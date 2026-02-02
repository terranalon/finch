"""Database initialization script with seed data."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Account,
    Asset,
    ExchangeRate,
    HistoricalSnapshot,
    Holding,
    HoldingLot,
    Portfolio,
    Transaction,
    User,
)
from app.services.auth import AuthService


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")


def seed_data(db: Session):
    """Seed the database with sample data for testing."""
    print("\nSeeding database with sample data...")

    # Create user
    print("Creating user...")
    user = User(
        id=str(uuid4()),
        email="john.doe@example.com",
        password_hash=AuthService.hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Create portfolio
    print("Creating portfolio...")
    portfolio = Portfolio(
        id=str(uuid4()),
        user_id=user.id,
        name="John's Portfolio",
        description="Main investment portfolio",
    )
    db.add(portfolio)
    db.flush()

    # Create accounts
    print("Creating accounts...")
    brokerage = Account(
        name="Interactive Brokers",
        institution="Interactive Brokers",
        account_type="Brokerage",
        currency="USD",
        account_number="U1234567",
        is_active=True,
    )
    brokerage.portfolios = [portfolio]

    pension = Account(
        name="Meitav Pension",
        institution="Meitav Dash",
        account_type="Pension",
        currency="ILS",
        account_number="P987654",
        is_active=True,
    )
    pension.portfolios = [portfolio]

    crypto_wallet = Account(
        name="Hardware Wallet",
        institution=None,
        account_type="SelfCustodied",
        currency="USD",
        is_active=True,
    )
    crypto_wallet.portfolios = [portfolio]

    db.add_all([brokerage, pension, crypto_wallet])
    db.flush()

    # Create assets
    print("Creating assets...")
    assets_data = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_class": "Stock",
            "sector": "Technology",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("175.50"),
            "last_fetched_at": datetime.now(),
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "asset_class": "Stock",
            "sector": "Technology",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("380.25"),
            "last_fetched_at": datetime.now(),
        },
        {
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "asset_class": "ETF",
            "sector": "Diversified",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("450.80"),
            "last_fetched_at": datetime.now(),
        },
        {
            "symbol": "BTC-USD",
            "name": "Bitcoin",
            "asset_class": "Crypto",
            "sector": "Cryptocurrency",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("43500.00"),
            "last_fetched_at": datetime.now(),
        },
        {
            "symbol": "ETH-USD",
            "name": "Ethereum",
            "asset_class": "Crypto",
            "sector": "Cryptocurrency",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("2280.50"),
            "last_fetched_at": datetime.now(),
        },
        {
            "symbol": "TEVA.TA",
            "name": "Teva Pharmaceutical Industries Ltd.",
            "asset_class": "Stock",
            "sector": "Healthcare",
            "data_source": "YahooFinance",
            "last_fetched_price": Decimal("38.50"),
            "last_fetched_at": datetime.now(),
        },
    ]

    assets = [Asset(**asset_data) for asset_data in assets_data]
    db.add_all(assets)
    db.flush()

    # Create holdings
    print("Creating holdings...")
    holdings_data = [
        {
            "account_id": brokerage.id,
            "asset_id": assets[0].id,  # AAPL
            "quantity": Decimal("50.00000000"),
            "cost_basis": Decimal("8500.00"),
            "strategy_horizon": "LongTerm",
            "is_active": True,
        },
        {
            "account_id": brokerage.id,
            "asset_id": assets[1].id,  # MSFT
            "quantity": Decimal("25.00000000"),
            "cost_basis": Decimal("9000.00"),
            "strategy_horizon": "LongTerm",
            "is_active": True,
        },
        {
            "account_id": brokerage.id,
            "asset_id": assets[2].id,  # SPY
            "quantity": Decimal("100.00000000"),
            "cost_basis": Decimal("42000.00"),
            "strategy_horizon": "MediumTerm",
            "is_active": True,
        },
        {
            "account_id": crypto_wallet.id,
            "asset_id": assets[3].id,  # BTC
            "quantity": Decimal("0.50000000"),
            "cost_basis": Decimal("20000.00"),
            "strategy_horizon": "LongTerm",
            "is_active": True,
        },
        {
            "account_id": crypto_wallet.id,
            "asset_id": assets[4].id,  # ETH
            "quantity": Decimal("5.00000000"),
            "cost_basis": Decimal("10000.00"),
            "strategy_horizon": "LongTerm",
            "is_active": True,
        },
        {
            "account_id": pension.id,
            "asset_id": assets[5].id,  # TEVA.TA
            "quantity": Decimal("1000.00000000"),
            "cost_basis": Decimal("35000.00"),
            "strategy_horizon": "LongTerm",
            "is_active": True,
        },
    ]

    holdings = [Holding(**holding_data) for holding_data in holdings_data]
    db.add_all(holdings)
    db.flush()

    # Create holding lots (FIFO tracking)
    print("Creating holding lots...")
    purchase_date_base = date.today() - timedelta(days=365)

    lots_data = [
        # AAPL lot
        {
            "holding_id": holdings[0].id,
            "quantity": Decimal("50.00000000"),
            "remaining_quantity": Decimal("50.00000000"),
            "cost_per_unit": Decimal("170.00"),
            "purchase_date": purchase_date_base,
            "fees": Decimal("5.00"),
            "is_closed": False,
        },
        # MSFT lot
        {
            "holding_id": holdings[1].id,
            "quantity": Decimal("25.00000000"),
            "remaining_quantity": Decimal("25.00000000"),
            "cost_per_unit": Decimal("360.00"),
            "purchase_date": purchase_date_base + timedelta(days=30),
            "fees": Decimal("5.00"),
            "is_closed": False,
        },
        # SPY lot 1
        {
            "holding_id": holdings[2].id,
            "quantity": Decimal("50.00000000"),
            "remaining_quantity": Decimal("50.00000000"),
            "cost_per_unit": Decimal("420.00"),
            "purchase_date": purchase_date_base + timedelta(days=60),
            "fees": Decimal("5.00"),
            "is_closed": False,
        },
        # SPY lot 2
        {
            "holding_id": holdings[2].id,
            "quantity": Decimal("50.00000000"),
            "remaining_quantity": Decimal("50.00000000"),
            "cost_per_unit": Decimal("420.00"),
            "purchase_date": purchase_date_base + timedelta(days=90),
            "fees": Decimal("5.00"),
            "is_closed": False,
        },
        # BTC lot
        {
            "holding_id": holdings[3].id,
            "quantity": Decimal("0.50000000"),
            "remaining_quantity": Decimal("0.50000000"),
            "cost_per_unit": Decimal("40000.00"),
            "purchase_date": purchase_date_base + timedelta(days=120),
            "fees": Decimal("50.00"),
            "is_closed": False,
        },
        # ETH lot
        {
            "holding_id": holdings[4].id,
            "quantity": Decimal("5.00000000"),
            "remaining_quantity": Decimal("5.00000000"),
            "cost_per_unit": Decimal("2000.00"),
            "purchase_date": purchase_date_base + timedelta(days=150),
            "fees": Decimal("25.00"),
            "is_closed": False,
        },
        # TEVA lot
        {
            "holding_id": holdings[5].id,
            "quantity": Decimal("1000.00000000"),
            "remaining_quantity": Decimal("1000.00000000"),
            "cost_per_unit": Decimal("35.00"),
            "purchase_date": purchase_date_base + timedelta(days=180),
            "fees": Decimal("20.00"),
            "is_closed": False,
        },
    ]

    lots = [HoldingLot(**lot_data) for lot_data in lots_data]
    db.add_all(lots)
    db.flush()

    # Create transactions
    print("Creating transactions...")
    transactions_data = [
        {
            "holding_id": holdings[0].id,
            "type": "Buy",
            "date": purchase_date_base,
            "quantity": Decimal("50.00000000"),
            "price_per_unit": Decimal("170.00"),
            "fees": Decimal("5.00"),
            "notes": "Initial AAPL purchase",
        },
        {
            "holding_id": holdings[1].id,
            "type": "Buy",
            "date": purchase_date_base + timedelta(days=30),
            "quantity": Decimal("25.00000000"),
            "price_per_unit": Decimal("360.00"),
            "fees": Decimal("5.00"),
            "notes": "Initial MSFT purchase",
        },
        {
            "holding_id": holdings[3].id,
            "type": "Buy",
            "date": purchase_date_base + timedelta(days=120),
            "quantity": Decimal("0.50000000"),
            "price_per_unit": Decimal("40000.00"),
            "fees": Decimal("50.00"),
            "notes": "BTC purchase",
        },
    ]

    transactions = [Transaction(**txn_data) for txn_data in transactions_data]
    db.add_all(transactions)
    db.flush()

    # Create exchange rates
    print("Creating exchange rates...")
    today = date.today()
    exchange_rates_data = [
        {
            "from_currency": "USD",
            "to_currency": "ILS",
            "date": today - timedelta(days=1),
            "rate": Decimal("3.65"),
        },
        {
            "from_currency": "USD",
            "to_currency": "ILS",
            "date": today,
            "rate": Decimal("3.67"),
        },
        {
            "from_currency": "ILS",
            "to_currency": "USD",
            "date": today,
            "rate": Decimal("0.2725"),
        },
    ]

    exchange_rates = [ExchangeRate(**rate_data) for rate_data in exchange_rates_data]
    db.add_all(exchange_rates)
    db.flush()

    # Create historical snapshots
    print("Creating historical snapshots...")
    snapshots_data = []
    for i in range(30):
        snapshot_date = today - timedelta(days=i)
        snapshots_data.extend(
            [
                {
                    "date": snapshot_date,
                    "account_id": brokerage.id,
                    "total_value_usd": Decimal("59500.00") + Decimal(i * 100),
                    "total_value_ils": Decimal("218215.00") + Decimal(i * 367),
                },
                {
                    "date": snapshot_date,
                    "account_id": crypto_wallet.id,
                    "total_value_usd": Decimal("30000.00") + Decimal(i * 50),
                    "total_value_ils": Decimal("110100.00") + Decimal(i * 183.5),
                },
                {
                    "date": snapshot_date,
                    "account_id": pension.id,
                    "total_value_usd": Decimal("10500.00") + Decimal(i * 20),
                    "total_value_ils": Decimal("38535.00") + Decimal(i * 73.4),
                },
            ]
        )

    snapshots = [HistoricalSnapshot(**snapshot_data) for snapshot_data in snapshots_data]
    db.add_all(snapshots)

    db.commit()
    print("Seed data created successfully!")
    print(f"  User: {user.email}")
    print(f"  Portfolio: {portfolio.name}")
    print(f"  Accounts: {len([brokerage, pension, crypto_wallet])}")


def init_db():
    """Initialize database with tables and seed data."""
    print("Initializing database...")

    # Create tables
    create_tables()

    # Seed data
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"\nDatabase already has {existing_users} users. Skipping seed data.")
            return

        seed_data(db)
        print("\nDatabase initialization complete!")

    except Exception as e:
        print(f"\nError during database initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
