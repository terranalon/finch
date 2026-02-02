"""Tests for email verification flow."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User


class TestRegistrationEmailVerification:
    """Tests for registration with email verification."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_sends_verification_email(self, mock_send, auth_client):
        """Registration should send verification email."""
        test_auth_client, _ = auth_client
        mock_send.return_value = True

        response = test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )
        assert response.status_code == 201
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == "test@example.com"

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_does_not_return_tokens(self, mock_send, auth_client):
        """Registration should not return auth tokens until email verified."""
        test_auth_client, _ = auth_client
        mock_send.return_value = True

        response = test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )
        data = response.json()
        assert "access_token" not in data
        assert "message" in data

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_register_creates_unverified_user(self, mock_send, auth_client):
        """Registration should create user with email_verified=False."""
        test_auth_client, db_session_maker = auth_client
        mock_send.return_value = True

        response = test_auth_client.post(
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
    def test_login_blocked_if_not_verified(self, mock_send, auth_client):
        """Login should fail if email not verified."""
        test_auth_client, _ = auth_client
        mock_send.return_value = True

        # Register (creates unverified user)
        test_auth_client.post(
            "/api/auth/register",
            json={"email": "unverified@example.com", "password": "Secure123"},
        )

        # Try to login
        response = test_auth_client.post(
            "/api/auth/login",
            json={"email": "unverified@example.com", "password": "Secure123"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "email_not_verified"

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_login_success_after_verification(self, mock_send, auth_client):
        """Login should succeed after email is verified."""
        test_auth_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register
        test_auth_client.post(
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
        response = test_auth_client.post(
            "/api/auth/login",
            json={"email": "verified@example.com", "password": "Secure123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestVerifyEmail:
    """Tests for verify-email endpoint."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    @patch("app.routers.auth.EmailService.send_welcome_email")
    def test_verify_email_success(self, mock_welcome, mock_verify, auth_client):
        """Valid token should verify email."""
        test_auth_client, db_session_maker = auth_client
        mock_verify.return_value = True
        mock_welcome.return_value = True

        # Register
        test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Get the verification token from the mock call
        token = mock_verify.call_args[0][1]

        # Verify email
        response = test_auth_client.post(
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

    def test_verify_email_invalid_token(self, auth_client):
        """Invalid token should be rejected."""
        test_auth_client, _ = auth_client

        response = test_auth_client.post(
            "/api/auth/verify-email",
            json={"token": "invalid-token"},
        )
        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_verify_email_expired_token(self, mock_send, auth_client):
        """Expired token should be rejected."""
        test_auth_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register
        test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Manually expire the token
        db = db_session_maker()
        token_record = db.query(EmailVerificationToken).first()
        token_record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

        # Get the original token
        token = mock_send.call_args[0][1]
        db.close()

        # Try to verify with expired token
        response = test_auth_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_verification_email")
    @patch("app.routers.auth.EmailService.send_welcome_email")
    def test_verify_email_used_token(self, mock_welcome, mock_verify, auth_client):
        """Already-used token should be rejected."""
        test_auth_client, _ = auth_client
        mock_verify.return_value = True
        mock_welcome.return_value = True

        # Register
        test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Get the token
        token = mock_verify.call_args[0][1]

        # Verify email (first time - should succeed)
        response = test_auth_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200

        # Try to verify again (should fail)
        response = test_auth_client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 400


class TestServiceAccountLogin:
    """Tests for service account login bypassing email verification."""

    def test_service_account_can_login_without_email_verification(self, auth_client):
        """Service accounts should be able to login even if email_verified=False."""
        test_auth_client, db_session_maker = auth_client
        from app.services.auth import AuthService

        # Create a service account with email_verified=False
        db = db_session_maker()
        service_user = User(
            email="test-service@system.internal",
            password_hash=AuthService.hash_password("ServicePass123"),
            is_service_account=True,
            email_verified=False,  # Explicitly unverified
            is_active=True,
        )
        db.add(service_user)
        db.commit()
        db.close()

        # Login should succeed despite email_verified=False
        response = test_auth_client.post(
            "/api/auth/login",
            json={"email": "test-service@system.internal", "password": "ServicePass123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestResendVerification:
    """Tests for resend-verification endpoint."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_creates_new_token(self, mock_send, auth_client):
        """Resend should create a new token and send email."""
        test_auth_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register
        test_auth_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Secure123"},
        )

        # Verify original token exists
        db = db_session_maker()
        assert db.query(EmailVerificationToken).first() is not None
        db.close()

        # Resend
        response = test_auth_client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

        # Check a new email was sent
        assert mock_send.call_count == 2

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_unknown_email_still_succeeds(self, mock_send, auth_client):
        """Resend should return success even for unknown email (no enumeration)."""
        test_auth_client, _ = auth_client
        mock_send.return_value = True

        response = test_auth_client.post(
            "/api/auth/resend-verification",
            json={"email": "unknown@example.com"},
        )
        # Should always return success to prevent email enumeration
        assert response.status_code == 200
        # But no email should have been sent
        mock_send.assert_not_called()

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_resend_already_verified_no_email(self, mock_send, auth_client):
        """Resend should not send email if already verified."""
        test_auth_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register
        test_auth_client.post(
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
        response = test_auth_client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        mock_send.assert_not_called()
