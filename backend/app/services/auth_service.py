"""Authentication service for password hashing and JWT management."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    # Pre-computed bcrypt hash for timing-consistent password verification
    # Used when user doesn't exist to prevent email enumeration via timing attacks
    _DUMMY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA9dWQ6E3Ky"

    @staticmethod
    def get_dummy_hash() -> str:
        """Get a dummy password hash for timing-consistent verification."""
        return AuthService._DUMMY_HASH

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token using SHA-256 (for refresh tokens that exceed bcrypt's 72-byte limit)."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_token_hash(token: str, hashed: str) -> bool:
        """Verify a token against its SHA-256 hash."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest() == hashed

    @staticmethod
    def create_access_token(
        user_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        expire = datetime.now(UTC) + expires_delta
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(
        user_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

        expire = datetime.now(UTC) + expires_delta
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_access_token(token: str) -> dict | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
