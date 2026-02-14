"""Tests for Portfolio model."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.portfolio import Portfolio
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from app.models.email_otp_code import EmailOtpCode
    from app.models.email_verification_token import EmailVerificationToken
    from app.models.mfa_temp_session import MfaTempSession
    from app.models.password_reset_token import PasswordResetToken
    from app.models.session import Session as UserSession
    from app.models.user_mfa import UserMfa
    from app.models.user_recovery_code import UserRecoveryCode

    engine = create_engine("sqlite:///:memory:")
    # Create all tables User references (for cascade deletes)
    User.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    # Account uses PostgreSQL JSONB which can't compile on SQLite,
    # so create the table via raw SQL with TEXT instead of JSONB.
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                institution VARCHAR(100),
                account_type VARCHAR(50) NOT NULL,
                currency VARCHAR(3) NOT NULL,
                account_number VARCHAR(100),
                external_id VARCHAR(100),
                is_active BOOLEAN DEFAULT 1,
                snapshot_status VARCHAR(20),
                broker_type VARCHAR(50),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS portfolio_accounts (
                portfolio_id VARCHAR(36) REFERENCES portfolios(id),
                account_id INTEGER REFERENCES accounts(id),
                added_at TIMESTAMP,
                PRIMARY KEY (portfolio_id, account_id)
            )
        """)
        )
    UserSession.__table__.create(engine, checkfirst=True)
    EmailVerificationToken.__table__.create(engine, checkfirst=True)
    PasswordResetToken.__table__.create(engine, checkfirst=True)
    UserMfa.__table__.create(engine, checkfirst=True)
    EmailOtpCode.__table__.create(engine, checkfirst=True)
    UserRecoveryCode.__table__.create(engine, checkfirst=True)
    MfaTempSession.__table__.create(engine, checkfirst=True)
    test_session = sessionmaker(bind=engine)
    session = test_session()
    yield session
    session.close()


def test_create_portfolio(db_session: Session):
    """Test creating a portfolio for a user."""
    user = User(email="test@example.com", username="test_user", password_hash="hash")
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
    user = User(email="test@example.com", username="test_user", password_hash="hash")
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
    user = User(email="test@example.com", username="test_user", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio = Portfolio(user_id=user.id, name="To Delete")
    db_session.add(portfolio)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.query(Portfolio).filter_by(user_id=user.id).all()
    assert len(remaining) == 0
