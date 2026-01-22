"""Integration tests for auth router."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.portfolio import Portfolio
from app.models.session import Session
from app.models.user import User
from app.rate_limiter import limiter


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    # Clear rate limiter storage between tests
    limiter.reset()

    # Use StaticPool to share same connection across all threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all auth-related tables
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    EmailVerificationToken.__table__.create(engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()


def register_and_verify_user(
    test_client, db_session_maker, email: str, password: str
) -> dict:
    """Helper to register and verify a user, then login to get tokens."""
    with patch("app.routers.auth.EmailService.send_verification_email"):
        test_client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )

    # Manually verify the user
    db = db_session_maker()
    user = db.query(User).filter(User.email == email).first()
    user.email_verified = True
    db.commit()
    db.close()

    # Login to get tokens
    response = test_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_success(mock_send, client):
    """Test successful registration returns message (not tokens)."""
    test_client, _ = client
    mock_send.return_value = True

    response = test_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    # Now returns message, not tokens (email verification required)
    assert "message" in data
    assert "access_token" not in data


@patch("app.routers.auth.EmailService.send_verification_email")
def test_register_duplicate_email(mock_send, client):
    """Test registration with duplicate email."""
    test_client, _ = client
    mock_send.return_value = True

    test_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    response = test_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Different123"},
    )
    assert response.status_code == 400


def test_register_short_password(client):
    """Test registration with password too short."""
    test_client, _ = client

    response = test_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert response.status_code == 422  # Validation error


def test_login_success(client):
    """Test successful login after email verification."""
    test_client, db_session_maker = client

    tokens = register_and_verify_user(
        test_client, db_session_maker, "test@example.com", "Secure123"
    )

    assert "access_token" in tokens
    assert "refresh_token" in tokens


@patch("app.routers.auth.EmailService.send_verification_email")
def test_login_wrong_password(mock_send, client):
    """Test login with wrong password."""
    test_client, db_session_maker = client
    mock_send.return_value = True

    # Register and verify
    test_client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    db = db_session_maker()
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.email_verified = True
    db.commit()
    db.close()

    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    test_client, _ = client

    response = test_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Secure123"},
    )
    assert response.status_code == 401


def test_refresh_token(client):
    """Test token refresh."""
    test_client, db_session_maker = client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_client, db_session_maker, "test@example.com", "Secure123"
    )

    # Refresh token
    response = test_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


def test_logout(client):
    """Test logout revokes the refresh token."""
    test_client, db_session_maker = client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_client, db_session_maker, "test@example.com", "Secure123"
    )

    # Logout
    response = test_client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

    # Try to refresh with old token - should fail
    response = test_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    """Test getting current user info when authenticated."""
    test_client, db_session_maker = client

    # Register, verify, and login
    tokens = register_and_verify_user(
        test_client, db_session_maker, "me@test.com", "TestPassword123"
    )

    # Get /me
    response = test_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"


def test_get_me_unauthenticated(client):
    """Test /auth/me without authentication returns 401."""
    test_client, _ = client

    response = test_client.get("/api/auth/me")
    assert response.status_code == 401
