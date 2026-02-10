"""Integration tests for auth router."""

from unittest.mock import patch

from app.models.user import User
from tests.conftest import register_and_verify_user

# --- Registration Tests ---


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_success(mock_send, auth_client):
    """Test successful registration returns message (not tokens)."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "Secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "access_token" not in data


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_stores_username(mock_send, auth_client):
    """Test registration stores username on the user record."""
    test_auth_client, db_session_maker = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "myuser", "password": "Secure123"},
    )

    db = db_session_maker()
    user = db.query(User).filter(User.email == "test@example.com").first()
    assert user.username == "myuser"
    db.close()


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_duplicate_email(mock_send, auth_client):
    """Test registration with duplicate email."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "user1", "password": "Secure123"},
    )
    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "user2", "password": "Different123"},
    )
    assert response.status_code == 400


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_duplicate_username(mock_send, auth_client):
    """Test registration with duplicate username returns 400."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "user1@example.com", "username": "taken", "password": "Secure123"},
    )
    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "username": "taken", "password": "Secure123"},
    )
    assert response.status_code == 400
    assert "username" in response.json()["detail"].lower()


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_username_case_insensitive(mock_send, auth_client):
    """Test username uniqueness is case-insensitive."""
    test_auth_client, _ = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "user1@example.com", "username": "TestUser", "password": "Secure123"},
    )
    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "username": "testuser", "password": "Secure123"},
    )
    assert response.status_code == 400


def test_register_short_password(auth_client):
    """Test registration with password too short."""
    test_auth_client, _ = auth_client

    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "short"},
    )
    assert response.status_code == 422


def test_register_invalid_username(auth_client):
    """Test registration with invalid username format."""
    test_auth_client, _ = auth_client

    response = test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "ab", "password": "Secure123"},
    )
    assert response.status_code == 422


# --- Login Tests ---


def test_login_success(auth_client):
    """Test successful login after email verification."""
    test_auth_client, db_session_maker = auth_client

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_with_username(auth_client):
    """Test login using username instead of email."""
    test_auth_client, db_session_maker = auth_client

    register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123", username="myuser"
    )

    response = test_auth_client.post(
        "/api/auth/login",
        json={"identifier": "myuser", "password": "Secure123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_username_case_insensitive(auth_client):
    """Test login by username is case-insensitive."""
    test_auth_client, db_session_maker = auth_client

    register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123", username="myuser"
    )

    response = test_auth_client.post(
        "/api/auth/login",
        json={"identifier": "MyUser", "password": "Secure123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@patch("app.routers.auth.EmailService.send_verification_email")
def test_login_wrong_password(mock_send, auth_client):
    """Test login with wrong password."""
    test_auth_client, db_session_maker = auth_client
    mock_send.return_value = True

    test_auth_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "Secure123"},
    )
    db = db_session_maker()
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.email_verified = True
    db.commit()
    db.close()

    response = test_auth_client.post(
        "/api/auth/login",
        json={"identifier": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(auth_client):
    """Test login with non-existent user."""
    test_auth_client, _ = auth_client

    response = test_auth_client.post(
        "/api/auth/login",
        json={"identifier": "nobody@example.com", "password": "Secure123"},
    )
    assert response.status_code == 401


# --- Token Tests ---


def test_refresh_token(auth_client):
    """Test token refresh."""
    test_auth_client, db_session_maker = auth_client

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

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

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "test@example.com", "Secure123"
    )

    response = test_auth_client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

    response = test_auth_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


# --- User Profile Tests ---


def test_get_me_authenticated(auth_client):
    """Test getting current user info when authenticated."""
    test_auth_client, db_session_maker = auth_client

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "me@test.com", "TestPassword123"
    )

    response = test_auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["username"] == "testuser"
    assert "name" not in data


def test_get_me_unauthenticated(auth_client):
    """Test /auth/me without authentication returns 401."""
    test_auth_client, _ = auth_client

    response = test_auth_client.get("/api/auth/me")
    assert response.status_code == 401


def test_update_username(auth_client):
    """Test updating username via PUT /me."""
    test_auth_client, db_session_maker = auth_client

    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "me@test.com", "TestPassword123", username="oldname"
    )

    response = test_auth_client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"username": "newname"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "newname"


def test_update_username_duplicate(auth_client):
    """Test updating to a taken username returns 400."""
    test_auth_client, db_session_maker = auth_client

    register_and_verify_user(
        test_auth_client, db_session_maker, "user1@test.com", "TestPassword123", username="taken"
    )
    tokens = register_and_verify_user(
        test_auth_client, db_session_maker, "user2@test.com", "TestPassword123", username="other"
    )

    response = test_auth_client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"username": "taken"},
    )
    assert response.status_code == 400
