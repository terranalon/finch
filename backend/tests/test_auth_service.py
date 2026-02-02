"""Tests for auth service."""

from datetime import timedelta

from app.services.auth import AuthService


def test_hash_password():
    """Test password hashing."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_password_correct():
    """Test verifying correct password."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert AuthService.verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test verifying incorrect password."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert AuthService.verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test creating access token."""
    user_id = "user-123"
    token = AuthService.create_access_token(user_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are long


def test_decode_access_token():
    """Test decoding access token."""
    user_id = "user-123"
    token = AuthService.create_access_token(user_id)
    decoded = AuthService.decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["type"] == "access"


def test_decode_expired_token():
    """Test that expired tokens fail."""
    user_id = "user-123"
    # Create token that expired 1 hour ago
    token = AuthService.create_access_token(
        user_id, expires_delta=timedelta(hours=-1)
    )
    decoded = AuthService.decode_access_token(token)

    assert decoded is None


def test_create_refresh_token():
    """Test creating refresh token."""
    user_id = "user-123"
    token = AuthService.create_refresh_token(user_id)

    assert token is not None
    decoded = AuthService.decode_access_token(token)
    assert decoded["type"] == "refresh"
