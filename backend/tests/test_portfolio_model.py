"""Tests for Portfolio model."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.portfolio import Portfolio
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from app.models.session import Session as UserSession

    engine = create_engine("sqlite:///:memory:")
    # Create all tables User references (for cascade deletes)
    User.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_portfolio(db_session: Session):
    """Test creating a portfolio for a user."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio = Portfolio(
        user_id=user.id,
        name="My Investments",
        description="Personal portfolio",
    )
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)

    assert portfolio.id is not None
    assert portfolio.user_id == user.id
    assert portfolio.name == "My Investments"


def test_user_has_multiple_portfolios(db_session: Session):
    """Test that a user can have multiple portfolios."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio1 = Portfolio(user_id=user.id, name="Personal")
    portfolio2 = Portfolio(user_id=user.id, name="Retirement")
    db_session.add_all([portfolio1, portfolio2])
    db_session.commit()

    db_session.refresh(user)
    assert len(user.portfolios) == 2


def test_portfolio_cascade_delete(db_session: Session):
    """Test that portfolios are deleted when user is deleted."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio = Portfolio(user_id=user.id, name="To Delete")
    db_session.add(portfolio)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.query(Portfolio).filter_by(user_id=user.id).all()
    assert len(remaining) == 0
