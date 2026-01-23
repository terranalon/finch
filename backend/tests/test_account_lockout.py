"""Tests for account lockout functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.user import User
from app.rate_limiter import limiter


class TestAccountLockout:
    """Tests for account lockout after failed login attempts."""

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_account_locks_after_max_failed_attempts(self, mock_send, auth_client):
        """Account should lock after 5 failed login attempts."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Password123"},
        )

        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        # Attempt 5 failed logins
        for i in range(5):
            response = test_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword"},
            )
            assert response.status_code == 401

        # Reset rate limiter so we can test lockout specifically
        limiter.reset()

        # 6th attempt should be blocked due to account lockout
        # Returns 401 (same as invalid credentials) to prevent email enumeration
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_correct_password_blocked_when_locked(self, mock_send, auth_client):
        """Even correct password should be blocked when account is locked."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Password123"},
        )

        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        # Lock the account with 5 failed attempts
        for _ in range(5):
            test_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword"},
            )

        # Reset rate limiter so we can test lockout specifically
        limiter.reset()

        # Try with correct password - should still be blocked
        # Returns 401 (same as invalid credentials) to prevent email enumeration
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        assert response.status_code == 401

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_successful_login_clears_failed_attempts(self, mock_send, auth_client):
        """Successful login should clear failed attempt counter."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Password123"},
        )

        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        # 3 failed attempts (below threshold)
        for _ in range(3):
            test_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword"},
            )

        # Successful login
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        assert response.status_code == 200

        # Verify counter was reset
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.failed_login_attempts == 0
        db.close()

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_lockout_expires_after_duration(self, mock_send, auth_client):
        """Lockout should expire after the configured duration."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Password123"},
        )

        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        # Manually set lockout in the past
        user.failed_login_attempts = 5
        user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
        db.close()

        # Login should work now (lockout expired)
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        assert response.status_code == 200

    @patch("app.routers.auth.EmailService.send_verification_email")
    def test_failed_login_increments_counter(self, mock_send, auth_client):
        """Each failed login should increment the counter."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Password123"},
        )

        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.email_verified = True
        db.commit()
        db.close()

        # 2 failed attempts
        for _ in range(2):
            test_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword"},
            )

        # Verify counter
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.failed_login_attempts == 2
        db.close()


class TestTimingAttackPrevention:
    """Tests for timing attack prevention on login."""

    @patch("app.routers.auth.AuthService.verify_password")
    @patch("app.routers.auth.AuthService.get_dummy_hash")
    def test_nonexistent_user_performs_dummy_verification(
        self, mock_get_dummy, mock_verify, auth_client
    ):
        """Non-existent user login should perform dummy verification for timing consistency."""
        test_client, _ = auth_client
        mock_get_dummy.return_value = "dummy_hash"
        mock_verify.return_value = False

        response = test_client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "AnyPassword123"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"
        mock_get_dummy.assert_called_once()
        mock_verify.assert_called_once_with("AnyPassword123", "dummy_hash")
