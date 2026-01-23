"""Service for logging security events."""

import json
import logging

from sqlalchemy.orm import Session

from app.models.security_audit_log import SecurityAuditLog

logger = logging.getLogger(__name__)


class SecurityEventType:
    """Constants for security event types."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_BLOCKED_UNVERIFIED = "login_blocked_unverified"
    LOGIN_BLOCKED_DISABLED = "login_blocked_disabled"
    LOGIN_BLOCKED_LOCKOUT = "login_blocked_lockout"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFIED = "email_verified"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_VERIFIED = "mfa_verified"
    MFA_FAILED = "mfa_failed"
    RECOVERY_CODE_USED = "recovery_code_used"
    ADMIN_MFA_DISABLED = "admin_mfa_disabled"


class SecurityAuditService:
    """Service for recording security audit events."""

    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Log a security event to the database."""
        log_entry = SecurityAuditLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details=json.dumps(details) if details else None,
        )
        db.add(log_entry)
        # Note: Caller is responsible for committing the transaction

        # Also log to application logger for monitoring
        logger.info(
            f"Security event: {event_type} | user_id={user_id} | ip={ip_address}"
        )

    @staticmethod
    def get_request_info(request) -> tuple[str | None, str | None]:
        """Extract IP address and user agent from a FastAPI request."""
        ip_address = None
        user_agent = None

        if request:
            # Get IP from X-Forwarded-For header (if behind proxy) or client host
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host

            user_agent = request.headers.get("User-Agent", "")[:500]

        return ip_address, user_agent
