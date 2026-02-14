"""Tests for demo user seeding script."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.portfolio import Portfolio
from app.models.session import Session
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.close()


def test_create_demo_user(db_session):
    """Test creating demo user with portfolio."""
    from scripts.seed_demo_user import create_demo_user

    user, portfolio, _ = create_demo_user(db_session)

    assert user.email == "demo@finch.com"
    assert user.is_active is True
    assert portfolio is not None
    assert portfolio.name == "Demo Portfolio"
    assert portfolio.user_id == user.id


def test_create_demo_user_idempotent(db_session):
    """Test that running seed twice doesn't create duplicates."""
    from scripts.seed_demo_user import create_demo_user

    user1, _, _ = create_demo_user(db_session)
    user2, _, _ = create_demo_user(db_session)

    assert user1.id == user2.id
    users = db_session.query(User).filter(User.email == "demo@finch.com").all()
    assert len(users) == 1
