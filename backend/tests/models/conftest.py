"""Shared test fixtures for model tests."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database for full compatibility."""
    db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Clean up test data (cascade from users handles portfolios, accounts via relationships)
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM portfolio_accounts WHERE 1=1"))
        conn.execute(text("DELETE FROM accounts WHERE 1=1"))
        conn.execute(text("DELETE FROM portfolios WHERE 1=1"))
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_%'"))
        conn.commit()


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    test_session_maker = sessionmaker(bind=test_db)
    session = test_session_maker()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test_many_to_many@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
