"""Tests for entity to portfolio migration script."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.portfolio import Portfolio
from app.models.session import Session as UserSession
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database with mock entity/account data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create auth tables
    User.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)

    # Create mock entities table (simulating existing data)
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER,
                portfolio_id TEXT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                currency TEXT NOT NULL
            )
        """)
        )
        # Insert test data
        conn.execute(
            text("INSERT INTO entities (id, name, type) VALUES (1, 'John Doe', 'Individual')")
        )
        conn.execute(
            text("INSERT INTO entities (id, name, type) VALUES (2, 'Jane Corp', 'Corporation')")
        )
        conn.execute(
            text(
                "INSERT INTO accounts (id, entity_id, name, account_type, currency) "
                "VALUES (1, 1, 'IBI Account', 'brokerage', 'ILS')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO accounts (id, entity_id, name, account_type, currency) "
                "VALUES (2, 1, 'Binance', 'crypto', 'USD')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO accounts (id, entity_id, name, account_type, currency) "
                "VALUES (3, 2, 'Corp Account', 'brokerage', 'USD')"
            )
        )
        conn.commit()

    testing_session_local = sessionmaker(bind=engine)
    session = testing_session_local()
    yield session
    session.close()


def test_migrate_creates_default_user(db_session):
    """Test migration creates a default user."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    result = migrate_entities(db_session)

    assert result["user_created"] is True
    user = db_session.query(User).filter(User.email == "migrated@finch.local").first()
    assert user is not None


def test_migrate_creates_portfolios_from_entities(db_session):
    """Test migration creates portfolio per entity."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    result = migrate_entities(db_session)

    assert result["portfolios_created"] == 2
    portfolios = db_session.query(Portfolio).all()
    assert len(portfolios) == 2
    names = {p.name for p in portfolios}
    assert "John Doe" in names
    assert "Jane Corp" in names


def test_migrate_links_accounts_to_portfolios(db_session):
    """Test migration links accounts to their new portfolios."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    migrate_entities(db_session)

    # Check accounts have portfolio_id set
    result = db_session.execute(
        text("SELECT id, portfolio_id FROM accounts WHERE portfolio_id IS NOT NULL")
    )
    rows = result.fetchall()
    assert len(rows) == 3  # All 3 accounts should have portfolio_id


def test_migrate_is_idempotent(db_session):
    """Test running migration twice doesn't create duplicates."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    migrate_entities(db_session)
    result = migrate_entities(db_session)

    assert result["portfolios_created"] == 0  # No new portfolios
    users = db_session.query(User).filter(User.email == "migrated@finch.local").all()
    assert len(users) == 1
