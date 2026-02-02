"""MFA service for TOTP, Email OTP, and recovery codes."""

import base64
import secrets
from io import BytesIO

import pyotp
import qrcode
from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet cipher for MFA secret encryption/decryption."""
    if not settings.mfa_encryption_key:
        raise ValueError("MFA encryption key not configured")
    return Fernet(settings.mfa_encryption_key.encode())


class MfaService:
    """Service for MFA operations."""

    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a new TOTP secret (base32 encoded, 32 characters)."""
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, email: str) -> str:
        """Get otpauth:// URI for QR code scanning."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name="Finch Portfolio")

    @staticmethod
    def generate_qr_code_base64(uri: str) -> str:
        """Generate QR code as base64 PNG for embedding in responses."""
        qr = qrcode.make(uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify TOTP code. Allows 1 window of drift (30 seconds each side)."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def encrypt_secret(secret: str) -> str:
        """Encrypt TOTP secret for storage using Fernet (AES-128-CBC).

        Requires mfa_encryption_key to be a valid Fernet key.
        Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        """
        return _get_fernet().encrypt(secret.encode()).decode()

    @staticmethod
    def decrypt_secret(encrypted: str) -> str:
        """Decrypt TOTP secret from storage."""
        return _get_fernet().decrypt(encrypted.encode()).decode()

    @staticmethod
    def generate_recovery_codes(count: int = 10) -> list[str]:
        """Generate recovery codes in XXXX-XXXX-XXXX format.

        Each code is unique and cryptographically random.
        """
        codes = []
        for _ in range(count):
            # 3 groups of 4 hex characters (uppercase)
            parts = [secrets.token_hex(2).upper() for _ in range(3)]
            codes.append("-".join(parts))
        return codes

    @staticmethod
    def generate_email_otp() -> str:
        """Generate 6-digit OTP code for email verification."""
        return f"{secrets.randbelow(1000000):06d}"
