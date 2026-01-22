"""Tests for auth dependency."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.portfolio import Portfolio
from app.models.session import Session
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def test_app():
    """Create test app with protected route."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = FastAPI()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": user.id, "email": user.email}

    # Create test user
    db = TestingSessionLocal()
    user = User(email="test@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    return TestClient(app), user_id


def test_protected_route_with_valid_token(test_app):
    """Test accessing protected route with valid token."""
    client, user_id = test_app
    token = AuthService.create_access_token(user_id)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id


def test_protected_route_without_token(test_app):
    """Test accessing protected route without token."""
    client, _ = test_app
    response = client.get("/protected")
    # HTTPBearer may return 401 or 403 depending on version
    assert response.status_code in (401, 403)


def test_protected_route_with_invalid_token(test_app):
    """Test accessing protected route with invalid token."""
    client, _ = test_app
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_protected_route_with_refresh_token(test_app):
    """Test that refresh token is rejected for access."""
    client, user_id = test_app
    # Create refresh token instead of access token
    token = AuthService.create_refresh_token(user_id)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
