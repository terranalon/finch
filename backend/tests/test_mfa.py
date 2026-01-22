"""Tests for Multi-Factor Authentication (MFA) flows."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.mfa_temp_session import MfaTempSession
from app.models.user import User
from tests.conftest import register_and_verify_user


class TestTotpSetup:
    """Tests for TOTP MFA setup."""

    def test_setup_totp_returns_secret_and_qr(self, auth_client):
        """Setup TOTP should return secret and QR code data."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code_base64" in data
        assert "manual_entry_key" in data
        assert len(data["secret"]) == 32  # Base32 encoded secret

    def test_setup_totp_requires_auth(self, auth_client):
        """Setup TOTP should require authentication."""
        test_client, _ = auth_client

        response = test_client.post("/api/auth/mfa/setup/totp")
        assert response.status_code == 401


class TestTotpConfirm:
    """Tests for TOTP confirmation."""

    @patch("app.services.mfa_service.MfaService.verify_totp")
    def test_confirm_totp_success(self, mock_verify, auth_client):
        """Confirming TOTP with valid code should enable MFA and return recovery codes."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # First get the setup secret
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        # Confirm with valid code
        response = test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) == 10
        assert data["message"] == "TOTP MFA enabled successfully"

        # Verify MFA is enabled in database
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.mfa is not None
        assert user.mfa.totp_enabled is True
        db.close()

    @patch("app.services.mfa_service.MfaService.verify_totp")
    def test_confirm_totp_invalid_code(self, mock_verify, auth_client):
        """Confirming TOTP with invalid code should fail."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = False

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Get setup secret
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        response = test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "000000"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


class TestEmailOtpSetup:
    """Tests for Email OTP setup."""

    def test_setup_email_otp_success(self, auth_client):
        """Setup Email OTP should enable email MFA."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        response = test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) == 10

        # Verify MFA is enabled in database
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.mfa is not None
        assert user.mfa.email_otp_enabled is True
        db.close()


class TestMfaDisable:
    """Tests for disabling MFA."""

    @patch("app.services.mfa_service.MfaService.verify_totp")
    @patch("app.routers.mfa.EmailService.send_mfa_disabled_notification")
    def test_disable_mfa_with_totp_code(self, mock_notify, mock_verify, auth_client):
        """Disabling MFA with valid TOTP code should succeed."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = True
        mock_notify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Setup and confirm TOTP
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Disable MFA (use content instead of json for DELETE)
        response = test_client.request(
            "DELETE",
            "/api/auth/mfa",
            content=json.dumps({"mfa_code": "123456"}),
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_notify.assert_called_once_with("test@example.com")

        # Verify MFA is disabled
        db = db_session_maker()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user.mfa is None or user.mfa.totp_enabled is False
        db.close()

    def test_disable_mfa_with_recovery_code(self, auth_client):
        """Disabling MFA with valid recovery code should succeed."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Setup email OTP (simpler than TOTP)
        setup_response = test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        recovery_codes = setup_response.json()["recovery_codes"]

        # Disable MFA with recovery code (use content instead of json for DELETE)
        with patch("app.routers.mfa.EmailService.send_mfa_disabled_notification"):
            response = test_client.request(
                "DELETE",
                "/api/auth/mfa",
                content=json.dumps({"recovery_code": recovery_codes[0]}),
                headers={
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200


class TestRecoveryCodes:
    """Tests for recovery code operations."""

    @patch("app.services.mfa_service.MfaService.verify_totp")
    def test_regenerate_recovery_codes(self, mock_verify, auth_client):
        """Regenerating recovery codes should return new codes and invalidate old ones."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Setup TOTP
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        confirm_response = test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        old_codes = confirm_response.json()["recovery_codes"]

        # Regenerate recovery codes
        response = test_client.post(
            "/api/auth/mfa/recovery-codes",
            json={"mfa_code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == 200
        new_codes = response.json()["recovery_codes"]
        assert len(new_codes) == 10
        # New codes should be different from old codes
        assert set(new_codes) != set(old_codes)


class TestMfaLoginFlow:
    """Tests for MFA login flow."""

    @patch("app.services.mfa_service.MfaService.verify_totp")
    def test_login_with_mfa_returns_temp_token(self, mock_verify, auth_client):
        """Login with MFA enabled should return temp token, not full tokens."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable TOTP MFA
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Now login again - should require MFA
        response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mfa_required"] is True
        assert "temp_token" in data
        assert "methods" in data
        assert "totp" in data["methods"]
        assert "access_token" not in data

    @patch("app.services.mfa_service.MfaService.verify_totp")
    def test_verify_mfa_returns_full_tokens(self, mock_verify, auth_client):
        """Verifying MFA should return full access/refresh tokens."""
        test_client, db_session_maker = auth_client
        mock_verify.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable TOTP MFA
        setup_response = test_client.post(
            "/api/auth/mfa/setup/totp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        secret = setup_response.json()["secret"]

        test_client.post(
            "/api/auth/mfa/confirm/totp",
            json={"secret": secret, "code": "123456"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Login to get temp token
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token = login_response.json()["temp_token"]

        # Verify MFA
        response = test_client.post(
            "/api/auth/mfa/verify",
            json={"temp_token": temp_token, "code": "123456", "method": "totp"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

    def test_verify_mfa_with_recovery_code(self, auth_client):
        """Verifying MFA with recovery code should work and consume the code."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable email OTP (simpler)
        setup_response = test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        recovery_codes = setup_response.json()["recovery_codes"]

        # Login to get temp token
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token = login_response.json()["temp_token"]

        # Verify with recovery code
        response = test_client.post(
            "/api/auth/mfa/verify",
            json={
                "temp_token": temp_token,
                "code": recovery_codes[0],
                "method": "recovery",
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

        # Same recovery code should not work again
        login_response2 = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token2 = login_response2.json()["temp_token"]

        response2 = test_client.post(
            "/api/auth/mfa/verify",
            json={
                "temp_token": temp_token2,
                "code": recovery_codes[0],
                "method": "recovery",
            },
        )
        assert response2.status_code == 401

    def test_verify_mfa_expired_temp_token(self, auth_client):
        """Verifying MFA with expired temp token should fail."""
        test_client, db_session_maker = auth_client

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable email OTP
        test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Login to get temp token
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token = login_response.json()["temp_token"]

        # Expire the temp session
        db = db_session_maker()
        temp_session = db.query(MfaTempSession).first()
        temp_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
        db.close()

        # Try to verify with expired token
        response = test_client.post(
            "/api/auth/mfa/verify",
            json={"temp_token": temp_token, "code": "123456", "method": "email"},
        )

        assert response.status_code == 401


class TestEmailOtpSend:
    """Tests for sending Email OTP codes."""

    @patch("app.routers.mfa.EmailService.send_mfa_otp_email")
    def test_send_email_otp(self, mock_send, auth_client):
        """Sending email OTP should create code and send email."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable email OTP
        test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Login to get temp token
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token = login_response.json()["temp_token"]

        # Request email OTP
        response = test_client.post(
            "/api/auth/mfa/send-email-code",
            json={"temp_token": temp_token},
        )

        assert response.status_code == 200
        mock_send.assert_called_once()
        # Email should be sent to the user's email
        assert mock_send.call_args[0][0] == "test@example.com"

    @patch("app.routers.mfa.EmailService.send_mfa_otp_email")
    def test_verify_email_otp(self, mock_send, auth_client):
        """Verifying email OTP should return full tokens."""
        test_client, db_session_maker = auth_client
        mock_send.return_value = True

        tokens = register_and_verify_user(
            test_client, db_session_maker, "test@example.com", "Password123"
        )

        # Enable email OTP
        test_client.post(
            "/api/auth/mfa/setup/email",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        # Login to get temp token
        login_response = test_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )
        temp_token = login_response.json()["temp_token"]

        # Request email OTP
        test_client.post(
            "/api/auth/mfa/send-email-code",
            json={"temp_token": temp_token},
        )

        # Get the code from the mock call
        code = mock_send.call_args[0][1]

        # Verify with the code
        response = test_client.post(
            "/api/auth/mfa/verify",
            json={"temp_token": temp_token, "code": code, "method": "email"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()
