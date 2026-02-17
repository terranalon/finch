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
from app.models.security_audit_log import SecurityAuditLog
from app.models.session import Session
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.models.user_recovery_code import UserRecoveryCode
from app.rate_limiter import limiter


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable rate limiter during tests to prevent 429 cascades."""
    limiter.enabled = False
    yield
    limiter.enabled = True


def register_and_verify_user(
    test_client: TestClient,
    db_session_maker,
    email: str,
    password: str,
    username: str = "testuser",
) -> dict:
    """Helper to register and verify a user, then login to get tokens."""
    with patch("app.routers.auth.EmailService.send_verification_email"):
        test_client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )

    db = db_session_maker()
    user = db.query(User).filter(User.email == email).first()
    user.email_verified = True
    db.commit()
    db.close()

    response = test_client.post(
        "/api/auth/login",
        json={"identifier": email, "password": password},
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
    SecurityAuditLog.__table__.create(engine, checkfirst=True)

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


def assert_error_response(
    response,
    status_code: int,
    *,
    error: str | None = None,
    message_contains: str | None = None,
) -> dict:
    """Assert response matches ErrorResponse format and return the body.

    Args:
        response: TestClient response
        status_code: Expected HTTP status code
        error: Expected error code (e.g., "NotFound")
        message_contains: Substring to find in the message (case-insensitive)

    Returns:
        The parsed response body for further assertions.
    """
    assert response.status_code == status_code
    body = response.json()
    assert "error" in body, f"Missing 'error' field in response: {body}"
    assert "message" in body, f"Missing 'message' field in response: {body}"
    assert "timestamp" in body, f"Missing 'timestamp' field in response: {body}"
    if error is not None:
        assert body["error"] == error, f"Expected error={error}, got {body['error']}"
    if message_contains is not None:
        assert message_contains.lower() in body["message"].lower(), (
            f"Expected '{message_contains}' in message, got: {body['message']}"
        )
    return body
