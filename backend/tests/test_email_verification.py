"""Tests for email verification flow."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.portfolio import Portfolio
from app.models.session import Session
from app.models.user import User
from app.rate_limiter import limiter
from app.services.auth_service import AuthService


@pytest.fixture
def client():
    """Create test client with in-memory database."""
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

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()


class TestRegistrationEmailVerification:
    """Tests for registration with email verification."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_sends_verification_email(self, mock_send, client):
        """Registration should send verification email."""
        test_client, _ = client
        mock_send.return_value = True

        response = test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )
        assert response.status_code == 201
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "test@example.com"

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_does_not_return_tokens(self, mock_send, client):
        """Registration should not return auth tokens until email verified."""
        test_client, _ = client
        mock_send.return_value = True

        response = test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )
        data = response.json()
        assert "access_token" not in data
        assert "message" in data

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_creates_unverified_user(self, mock_send, client):
        """Registration should create user with email_verified=False."""
        test_client, db_session_maker = client
        mock_send.return_value = True

        response = test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )
        assert response.status_code == 201

        # Check user was created with email_verified=False
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user is not None
        assert user.email_verified is False
        db.close()


class TestLoginEmailVerification:
    """Tests for login with email verification check."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_login_blocked_if_not_verified(self, mock_send, client):
        """Login should fail if email not verified."""
        test_client, _ = client
        mock_send.return_value = True

        # Register (creates unverified user)
        test_client.post(
            "/api/auth/register",
            json={"email": "unverified@example.com", "password": "Secure123"},
        )

        # Try to login
        response = test_client.post(
            "/api/auth/login",
            json={"email": "unverified@example.com", "password": "Secure123"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "email_not_verified"

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_login_success_after_verification(self, mock_send, client):
        """Login should succeed after email is verified."""
        test_client, db_session_maker = client
        mock_send.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "verified@example.com", "password": "Secure123"},
        )

        # Manually verify user
        db = db_session_maker()
        user = db.query(User).filter(User.email == "verified@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        # Login should now work
        response = test_client.post(
            "/api/auth/login",
            json={"email": "verified@example.com", "password": "Secure123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestVerifyEmail:
    """Tests for verify-email endpoint."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    @patch("app.routers.auth.EmailService.send_welcome_email")
    def test_verify_email_success(self, mock_welcome, mock_verify, client):
        """Valid token should verify email."""
        test_client, db_session_maker = client
        mock_verify.return_value = True
        mock_welcome.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Get the verification token from the mock call
        token = mock_verify.call_args[0][1]

        # Verify email
        response = test_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

        # Check user is now verified
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.email_verified is True
        db.close()

        # Welcome email should have been sent
        mock_welcome.assert_called_once_with("test@example.com")

    def test_verify_email_invalid_token(self, client):
        """Invalid token should be rejected."""
        test_client, _ = client

        response = test_client.post(
            "/api/auth/verify-email",
            json={"token": "invalid-token"},
        )
        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_verify_email_expired_token(self, mock_send, client):
        """Expired token should be rejected."""
        test_client, db_session_maker = client
        mock_send.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Manually expire the token
        db = db_session_maker()
        token_record = db.query(EmailVerificationToken).first()
        token_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        # Get the original token
        token = mock_send.call_args[0][1]
        db.close()

        # Try to verify with expired token
        response = test_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_verification_email")
    @patch("app.routers.auth.EmailService.send_welcome_email")
    def test_verify_email_used_token(self, mock_welcome, mock_verify, client):
        """Already-used token should be rejected."""
        test_client, _ = client
        mock_verify.return_value = True
        mock_welcome.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Get the token
        token = mock_verify.call_args[0][1]

        # Verify email (first time - should succeed)
        response = test_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200

        # Try to verify again (should fail)
        response = test_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 400


class TestResendVerification:
    """Tests for resend-verification endpoint."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_creates_new_token(self, mock_send, client):
        """Resend should create a new token and send email."""
        test_client, db_session_maker = client
        mock_send.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Get original token count
        db = db_session_maker()
        original_token = db.query(EmailVerificationToken).first()
        original_token_id = original_token.id
        db.close()

        # Resend
        response = test_client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

        # Check a new email was sent
        assert mock_send.call_count == 2

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_unknown_email_still_succeeds(self, mock_send, client):
        """Resend should return success even for unknown email (no enumeration)."""
        test_client, _ = client
        mock_send.return_value = True

        response = test_client.post(
            "/api/auth/resend-verification",
            json={"email": "unknown@example.com"},
        )
        # Should always return success to prevent email enumeration
        assert response.status_code == 200
        # But no email should have been sent
        mock_send.assert_not_called()

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_already_verified_no_email(self, mock_send, client):
        """Resend should not send email if already verified."""
        test_client, db_session_maker = client
        mock_send.return_value = True

        # Register
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Manually verify user
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        mock_send.reset_mock()

        # Resend should return success but not send email
        response = test_client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        mock_send.assert_not_called()
