"""Tests for User model."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from app.models.portfolio import Portfolio
    from app.models.session import Session

    engine = create_engine("sqlite:///:memory:")
    # Create all tables User references (for cascade deletes)
    User.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_user_with_password(db_session: Session):
    """Test creating a user with email and password."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password_here"
    assert user.google_id is None
    assert user.is_active is True


def test_create_user_with_google(db_session: Session):
    """Test creating a user with Google OAuth."""
    user = User(
        email="google@example.com",
        google_id="google_123456",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "google@example.com"
    assert user.password_hash is None
    assert user.google_id == "google_123456"


def test_user_email_unique(db_session: Session):
    """Test that user emails are unique."""
    user1 = User(email="same@example.com", password_hash="hash1")
    db_session.add(user1)
    db_session.commit()

    user2 = User(email="same@example.com", password_hash="hash2")
    db_session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()
