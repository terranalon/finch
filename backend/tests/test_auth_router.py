"""Integration tests for auth router."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
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

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_register_success(client):
    """Test successful registration returns tokens and user info."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    # Now returns TokenResponse with user info
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "test@example.com"
    assert "id" in data["user"]


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Different123"},
    )
    assert response.status_code == 400


def test_register_short_password(client):
    """Test registration with password too short."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert response.status_code == 422  # Validation error


def test_login_success(client):
    """Test successful login."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    """Test login with wrong password."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Secure123"},
    )
    assert response.status_code == 401


def test_refresh_token(client):
    """Test token refresh."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    tokens = login_response.json()

    # Refresh token
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # Note: access tokens may be identical if created within same second (same iat/exp)
    # The important thing is that refresh works and returns valid tokens


def test_logout(client):
    """Test logout revokes the refresh token."""
    # Register (now returns tokens directly)
    register_response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Secure123"},
    )
    tokens = register_response.json()

    # Logout
    response = client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

    # Try to refresh with old token - should fail
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    """Test getting current user info when authenticated."""
    # Register
    register_response = client.post(
        "/api/auth/register",
        json={"email": "me@test.com", "password": "TestPassword123"},
    )
    token = register_response.json()["access_token"]

    # Get /me
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"


def test_get_me_unauthenticated(client):
    """Test /auth/me without authentication returns 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
