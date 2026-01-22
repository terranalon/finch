"""Tests for Session model."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from app.models.session import Session
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from app.models.portfolio import Portfolio

    engine = create_engine("sqlite:///:memory:")
    # Create all tables User references (for cascade deletes)
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_session(db_session: DBSession):
    """Test creating a session for a user."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = Session(
        user_id=user.id,
        refresh_token_hash="hashed_refresh_token",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.refresh_token_hash == "hashed_refresh_token"
    assert session.is_revoked is False


def test_session_cascade_delete(db_session: DBSession):
    """Test that sessions are deleted when user is deleted."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = Session(
        user_id=user.id,
        refresh_token_hash="token",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.query(Session).filter_by(user_id=user.id).all()
    assert len(remaining) == 0
