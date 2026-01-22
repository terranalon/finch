"""Shared test fixtures for authentication tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.email_otp_code import EmailOtpCode
from app.models.email_verification_token import EmailVerificationToken
from app.models.mfa_temp_session import MfaTempSession
from app.models.password_reset_token import PasswordResetToken
from app.models.portfolio import Portfolio
from app.models.session import Session
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.models.user_recovery_code import UserRecoveryCode
from app.rate_limiter import limiter


def register_and_verify_user(
    test_client: TestClient, db_session_maker, email: str, password: str
) -> dict:
    """Helper to register and verify a user, then login to get tokens."""
    with patch("app.routers.auth.EmailService.send_verification_email"):
        test_client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )

    db = db_session_maker()
    user = db.query(User).filter(User.email == email).first()
    user.email_verified = True
    db.commit()
    db.close()

    response = test_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()


@pytest.fixture
def auth_client():
    """Create test client with in-memory database for auth tests.

    Yields a tuple of (TestClient, SessionMaker) for use in tests.
    """
    limiter.reset()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all auth-related tables
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    EmailVerificationToken.__table__.create(engine, checkfirst=True)
    PasswordResetToken.__table__.create(engine, checkfirst=True)
    UserMfa.__table__.create(engine, checkfirst=True)
    EmailOtpCode.__table__.create(engine, checkfirst=True)
    UserRecoveryCode.__table__.create(engine, checkfirst=True)
    MfaTempSession.__table__.create(engine, checkfirst=True)

    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, testing_session_local

    app.dependency_overrides.clear()
