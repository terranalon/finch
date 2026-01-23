"""Integration tests for auth router."""

from unittest.mock import patch

from app.models.user import User
from tests.conftest import register_and_verify_user


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_success(mock_send, auth_client):
    """Test successful registration returns message (not tokens)."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    # Now returns message, not tokens (email verification required)
    assert "message" in data
    assert "access_token" not in data


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_duplicate_email(mock_send, auth_client):
    """Test registration with duplicate email."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Different123"},
    )
    assert response.status_code == 400


def test_register_short_password(auth_client):
    """Test registration with password too short."""
    test_auth_client, _ = auth_client

    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert response.status_code == 422  # Validation error


def test_login_success(auth_client):
    """Test successful login after email verification."""
    test_auth_client, db_session_maker = auth_client

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

    assert "access_token" in tokens
    assert "refresh_token" in tokens


@patch("app.routers.auth.EmailService.send_verification_email")
def test_login_wrong_password(mock_send, auth_client):
    """Test login with wrong password."""
    test_auth_client, db_session_maker = auth_client
    mock_send.return_value = True

    # Register and verify
    test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    db = db_session_maker()
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.email_verified = True
    db.commit()
    db.close()

    response = test_auth_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(auth_client):
    """Test login with non-existent user."""
    test_auth_client, _ = auth_client

    response = test_auth_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Secure123"},
    )
    assert response.status_code == 401


def test_refresh_token(auth_client):
    """Test token refresh."""
    test_auth_client, db_session_maker = auth_client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

    # Refresh token
    response = test_auth_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


def test_logout(auth_client):
    """Test logout revokes the refresh token."""
    test_auth_client, db_session_maker = auth_client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

    # Logout
    response = test_auth_client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

    # Try to refresh with old token - should fail
    response = test_auth_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


def test_get_me_authenticated(auth_client):
    """Test getting current user info when authenticated."""
    test_auth_client, db_session_maker = auth_client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "me@test.com", "TestPassword123"
    )

    # Get /me
    response = test_auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"


def test_get_me_unauthenticated(auth_client):
    """Test /auth/me without authentication returns 401."""
    test_auth_client, _ = auth_client

    response = test_auth_client.get("/api/auth/me")
    assert response.status_code == 401
