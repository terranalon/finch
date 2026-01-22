"""Email service using SendGrid."""

import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending transactional emails via SendGrid."""

    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Send email via SendGrid. Returns True if successful."""
        if not settings.sendgrid_api_key:
            logger.warning("SendGrid API key not configured, skipping email send")
            return False

        message = Mail(
            from_email=(settings.email_from_address, settings.email_from_name),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        try:
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)
            logger.info(f"Email sent to {to_email}, status: {response.status_code}")
            return response.status_code in (200, 201, 202)
        except Exception:
            logger.exception(f"Failed to send email to {to_email}")
            return False

    @classmethod
    def send_verification_email(cls, email: str, token: str) -> bool:
        """Send email verification link."""
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        html = f"""
        <h2>Verify Your Email</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link expires in 24 hours.</p>
        <p>If you didn't create an account, you can ignore this email.</p>
        """
        return cls._send_email(email, "Verify Your Email - Finch Portfolio", html)

    @classmethod
    def send_welcome_email(cls, email: str) -> bool:
        """Send welcome email after verification."""
        login_url = f"{settings.frontend_url}/login"
        html = f"""
        <h2>Welcome to Finch Portfolio!</h2>
        <p>Your email has been verified. You can now log in to your account.</p>
        <p><a href="{login_url}">Log in to Finch Portfolio</a></p>
        """
        return cls._send_email(email, "Welcome to Finch Portfolio!", html)

    @classmethod
    def send_password_reset_email(cls, email: str, token: str) -> bool:
        """Send password reset link."""
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        html = f"""
        <h2>Reset Your Password</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link expires in 1 hour.</p>
        <p>If you didn't request this, you can ignore this email.</p>
        """
        return cls._send_email(email, "Reset Your Password - Finch Portfolio", html)

    @classmethod
    def send_mfa_otp_email(cls, email: str, code: str) -> bool:
        """Send MFA one-time code."""
        html = f"""
        <h2>Your Login Code</h2>
        <p>Your verification code is:</p>
        <h1 style="font-size: 32px; letter-spacing: 8px; font-family: monospace;">{code}</h1>
        <p>This code expires in 5 minutes.</p>
        <p>If you didn't try to log in, please secure your account immediately.</p>
        """
        return cls._send_email(email, f"Your Login Code: {code}", html)

    @classmethod
    def send_password_changed_notification(cls, email: str) -> bool:
        """Notify user their password was changed."""
        html = """
        <h2>Password Changed</h2>
        <p>Your password was successfully changed.</p>
        <p>If you didn't make this change, please contact support immediately.</p>
        """
        return cls._send_email(email, "Your Password Was Changed - Finch Portfolio", html)

    @classmethod
    def send_mfa_disabled_notification(cls, email: str) -> bool:
        """Notify user their MFA was disabled."""
        html = """
        <h2>Two-Factor Authentication Disabled</h2>
        <p>Two-factor authentication has been disabled on your account.</p>
        <p>If you didn't make this change, please contact support immediately.</p>
        """
        return cls._send_email(email, "MFA Disabled - Finch Portfolio", html)
