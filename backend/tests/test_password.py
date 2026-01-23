"""Tests for password change and reset flows."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from tests.conftest import register_and_verify_user


class TestChangePassword:
    """Tests for change-password endpoint."""

    def test_change_password_success(self, auth_client):
        """Change password with correct current password should succeed."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        with patch("app.routers.auth.EmailService.send_password_changed_notification"):
            response = test_client.put(
                "/api/auth/change-password",
                json={
                    "current_password": "OldPassword123",
                    "new_password": "NewPassword456",
                },
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        assert response.status_code == 200
        assert "changed" in response.json()["message"].lower()

        # Verify can login with new password
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456"},
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(self, auth_client):
        """Change password with wrong current password should fail."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        response = test_client.put(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewPassword456",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 401

    def test_change_password_invalidates_other_sessions(self, auth_client):
        """Change password should invalidate all other sessions."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        # Create a second session by logging in again
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "OldPassword123"},
        )
        second_tokens = login_response.json()

        # Change password using first session
        with patch("app.routers.auth.EmailService.send_password_changed_notification"):
            response = test_client.put(
                "/api/auth/change-password",
                json={
                    "current_password": "OldPassword123",
                    "new_password": "NewPassword456",
                },
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
        assert response.status_code == 200

        # Second session's refresh token should be revoked
        response = test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": second_tokens["refresh_token"]},
        )
        assert response.status_code == 401

    def test_change_password_weak_password_rejected(self, auth_client):
        """Change password with weak password should be rejected."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        response = test_client.put(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "weak",  # Too short, no uppercase, no number
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 422

    @patch("app.routers.auth.EmailService.send_password_changed_notification")
    def test_change_password_sends_notification(self, mock_notify, auth_client):
        """Change password should send notification email."""
        test_client, db_session_maker = auth_client
        mock_notify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        response = test_client.put(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword456",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        mock_notify.assert_called_once_with("test@example.com")


class TestForgotPassword:
    """Tests for forgot-password endpoint."""

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    def test_forgot_password_sends_email(self, mock_send, auth_client):
        """Forgot password should send reset email for existing user."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        # Register and verify user
        register_and_verify_user(test_client, db_session_maker, "test@example.com", "Password123")

        response = test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "test@example.com"

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    def test_forgot_password_unknown_email_still_succeeds(self, mock_send, auth_client):
        """Forgot password should return success for unknown email (no enumeration)."""
        test_client, _ = auth_client
        mock_send.return_value = True

        response = test_client.post(
            "/api/auth/forgot-password",
            json={"email": "unknown@example.com"},
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200
        # But no email should be sent
        mock_send.assert_not_called()

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    def test_forgot_password_creates_token(self, mock_send, auth_client):
        """Forgot password should create a reset token."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        register_and_verify_user(test_client, db_session_maker, "test@example.com", "Password123")

        response = test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200

        # Verify token was created
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        assert token is not None
        db.close()


class TestResetPassword:
    """Tests for reset-password endpoint."""

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    @patch("app.routers.auth.EmailService.send_password_changed_notification")
    def test_reset_password_success(self, mock_notify, mock_reset, auth_client):
        """Reset password with valid token should succeed."""
        test_client, db_session_maker = auth_client
        mock_reset.return_value = True
        mock_notify.return_value = True

        register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        # Request password reset
        test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        # Get the token from the mock call
        token = mock_reset.call_args[0][1]

        # Reset password
        response = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPassword456"},
        )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

        # Verify can login with new password
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456"},
        )
        assert response.status_code == 200

    def test_reset_password_invalid_token(self, auth_client):
        """Reset password with invalid token should fail."""
        test_client, _ = auth_client

        response = test_client.post(
            "/api/auth/reset-password",
            json={"token": "invalid-token", "new_password": "NewPassword456"},
        )

        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    def test_reset_password_expired_token(self, mock_send, auth_client):
        """Reset password with expired token should fail."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        # Request password reset
        test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        # Expire the token
        db = db_session_maker()
        token_record = db.query(PasswordResetToken).first()
        token_record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()

        token = mock_send.call_args[0][1]
        db.close()

        # Try to reset with expired token
        response = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPassword456"},
        )

        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    @patch("app.routers.auth.EmailService.send_password_changed_notification")
    def test_reset_password_used_token(self, mock_notify, mock_reset, auth_client):
        """Reset password with already-used token should fail."""
        test_client, db_session_maker = auth_client
        mock_reset.return_value = True
        mock_notify.return_value = True

        register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        # Request password reset
        test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        token = mock_reset.call_args[0][1]

        # Reset password (first time - should succeed)
        response = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPassword456"},
        )
        assert response.status_code == 200

        # Try to reset again (should fail)
        response = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "AnotherPassword789"},
        )
        assert response.status_code == 400

    @patch("app.routers.auth.EmailService.send_password_reset_email")
    @patch("app.routers.auth.EmailService.send_password_changed_notification")
    def test_reset_password_invalidates_all_sessions(self, mock_notify, mock_reset, auth_client):
        """Reset password should invalidate all existing sessions."""
        test_client, db_session_maker = auth_client
        mock_reset.return_value = True
        mock_notify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "OldPassword123"
        )

        # Request and complete password reset
        test_client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        reset_token = mock_reset.call_args[0][1]

        test_client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": "NewPassword456"},
        )

        # Old session's refresh token should be revoked
        response = test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 401
