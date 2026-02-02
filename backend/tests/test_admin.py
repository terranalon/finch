"""Tests for admin endpoints."""

import json
from unittest.mock import patch

import pytest

from app.models.security_audit_log import SecurityAuditLog
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.rate_limiter import limiter
from app.services.auth import MfaService


def _create_verified_user(
    test_client, db_session_maker, email: str, password: str, is_admin: bool = False
) -> tuple[str, str]:
    """Create and verify a user, returning (user_id, access_token)."""
    with patch("app.routers.auth.EmailService.send_verification_email"):
        test_client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )

    db = db_session_maker()
    user = db.query(User).filter(User.email == email).first()
    user.email_verified = True
    if is_admin:
        user.is_admin = True
    db.commit()
    user_id = user.id
    db.close()

    response = test_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    access_token = response.json()["access_token"]

    return user_id, access_token


def _enable_mfa_for_user(db_session_maker, user_id: str) -> None:
    """Enable TOTP MFA for a user."""
    db = db_session_maker()
    mfa = UserMfa(
        user_id=user_id,
        totp_enabled=True,
        totp_secret_encrypted=MfaService.encrypt_secret("TESTSECRET123456"),
        primary_method="totp",
    )
    db.add(mfa)
    db.commit()
    db.close()


class TestAdminDisableMfa:
    """Tests for admin MFA disable endpoint."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset rate limiter before each test."""
        limiter.reset()

    def test_admin_can_disable_user_mfa(self, auth_client):
        """Admin should be able to disable MFA for any user."""
        test_client, db_session_maker = auth_client

        _, admin_token = _create_verified_user(
            test_client, db_session_maker, "admin@example.com", "AdminPass123", is_admin=True
        )
        target_user_id, _ = _create_verified_user(
            test_client, db_session_maker, "target@example.com", "TargetPass123"
        )
        _enable_mfa_for_user(db_session_maker, target_user_id)

        with patch("app.routers.admin.EmailService.send_mfa_disabled_notification"):
            response = test_client.post(
                f"/api/admin/users/{target_user_id}/disable-mfa",
                json={"reason": "User requested via support ticket"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        assert "disabled" in response.json()["message"].lower()

        db = db_session_maker()
        mfa = db.query(UserMfa).filter(UserMfa.user_id == target_user_id).first()
        assert mfa is None
        db.close()

    def test_non_admin_cannot_disable_mfa(self, auth_client):
        """Non-admin users should not be able to disable MFA."""
        test_client, db_session_maker = auth_client

        user_id, token = _create_verified_user(
            test_client, db_session_maker, "regular@example.com", "RegularPass123"
        )

        response = test_client.post(
            f"/api/admin/users/{user_id}/disable-mfa",
            json={"reason": "Malicious attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_admin_disable_mfa_requires_reason(self, auth_client):
        """Admin must provide reason when disabling MFA."""
        test_client, db_session_maker = auth_client

        _, admin_token = _create_verified_user(
            test_client, db_session_maker, "admin@example.com", "AdminPass123", is_admin=True
        )

        response = test_client.post(
            "/api/admin/users/some-user-id/disable-mfa",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 422

    def test_admin_disable_mfa_user_not_found(self, auth_client):
        """Should return 404 if target user does not exist."""
        test_client, db_session_maker = auth_client

        _, admin_token = _create_verified_user(
            test_client, db_session_maker, "admin@example.com", "AdminPass123", is_admin=True
        )

        response = test_client.post(
            "/api/admin/users/nonexistent-user-id/disable-mfa",
            json={"reason": "Test reason"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_admin_disable_mfa_sends_notification(self, auth_client):
        """Should send notification email to user when MFA is disabled."""
        test_client, db_session_maker = auth_client

        _, admin_token = _create_verified_user(
            test_client, db_session_maker, "admin@example.com", "AdminPass123", is_admin=True
        )
        target_user_id, _ = _create_verified_user(
            test_client, db_session_maker, "target@example.com", "TargetPass123"
        )
        _enable_mfa_for_user(db_session_maker, target_user_id)

        with patch("app.routers.admin.EmailService.send_mfa_disabled_notification") as mock_notify:
            mock_notify.return_value = True
            response = test_client.post(
                f"/api/admin/users/{target_user_id}/disable-mfa",
                json={"reason": "User requested via support ticket"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            mock_notify.assert_called_once_with("target@example.com")

    def test_admin_disable_mfa_logs_security_event(self, auth_client):
        """Should log security audit event when admin disables MFA."""
        test_client, db_session_maker = auth_client

        admin_id, admin_token = _create_verified_user(
            test_client, db_session_maker, "admin@example.com", "AdminPass123", is_admin=True
        )
        target_user_id, _ = _create_verified_user(
            test_client, db_session_maker, "target@example.com", "TargetPass123"
        )
        _enable_mfa_for_user(db_session_maker, target_user_id)

        with patch("app.routers.admin.EmailService.send_mfa_disabled_notification"):
            response = test_client.post(
                f"/api/admin/users/{target_user_id}/disable-mfa",
                json={"reason": "User requested via support ticket"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200

        db = db_session_maker()
        log = (
            db.query(SecurityAuditLog)
            .filter(SecurityAuditLog.event_type == "admin_mfa_disabled")
            .first()
        )
        assert log is not None
        assert log.user_id == target_user_id
        details = json.loads(log.details)
        assert details["admin_id"] == admin_id
        assert details["reason"] == "User requested via support ticket"
        db.close()
