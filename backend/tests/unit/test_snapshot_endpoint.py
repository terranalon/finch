"""Tests for the synthetic snapshot import endpoint.

Tests POST /api/brokers/ibkr/snapshot/{account_id} which creates synthetic
transactions from current IBKR positions for instant onboarding.
"""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.portfolio import Portfolio
from app.models.session import Session as UserSession
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
def test_db():
    """Create a test database with required tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create auth tables
    User.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)

    # Create accounts table with all needed columns
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER,
                portfolio_id TEXT,
                name TEXT NOT NULL,
                institution TEXT,
                account_type TEXT NOT NULL,
                currency TEXT NOT NULL,
                account_number TEXT,
                external_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                snapshot_status TEXT,
                broker_type TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        # Create portfolio_accounts join table for many-to-many relationship
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS portfolio_accounts (
                portfolio_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (portfolio_id, account_id)
            )
        """)
        )
        conn.commit()

    return engine


@pytest.fixture
def client_with_user(test_db):
    """Create test client with a user, portfolio, and IBKR account."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_db)

    # Create test user and portfolio
    db = testing_session_local()
    user = User(email="test@example.com", password_hash=AuthService.hash_password("test123"))
    db.add(user)
    db.commit()
    db.refresh(user)

    portfolio = Portfolio(user_id=user.id, name="Test Portfolio")
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    # Create a test account with IBKR credentials
    with test_db.connect() as conn:
        metadata = json.dumps(
            {
                "ibkr": {"flex_token": "test_token", "flex_query_id": "test_query_id"},
            }
        )
        conn.execute(
            text("""
            INSERT INTO accounts (id, portfolio_id, name, account_type, currency, broker_type, metadata)
            VALUES (1, :portfolio_id, 'Test IBKR', 'Brokerage', 'USD', 'ibkr', :metadata)
        """),
            {"portfolio_id": portfolio.id, "metadata": metadata},
        )
        # Link account to portfolio via portfolio_accounts join table
        conn.execute(
            text("""
            INSERT INTO portfolio_accounts (portfolio_id, account_id)
            VALUES (:portfolio_id, 1)
        """),
            {"portfolio_id": portfolio.id},
        )
        conn.commit()

    user_id = user.id
    db.close()

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, user_id

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client_with_user):
    """Get auth headers for requests."""
    _, user_id = client_with_user
    token = AuthService.create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestSnapshotEndpoint:
    """Tests for POST /api/brokers/ibkr/snapshot/{account_id}."""

    def test_snapshot_endpoint_returns_200_on_success(self, client_with_user, auth_headers):
        """Snapshot endpoint should return 200 with completed status on success."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service:
            mock_service.import_snapshot.return_value = {
                "status": "completed",
                "source_type": "synthetic",
                "positions_imported": 3,
                "cash_balances": {"USD": 5000},
                "assets_created": 2,
            }

            response = client.post("/api/brokers/ibkr/snapshot/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["account_id"] == 1
        assert "stats" in data
        assert data["stats"]["positions_imported"] == 3

    def test_snapshot_endpoint_calls_service_with_credentials(self, client_with_user, auth_headers):
        """Snapshot endpoint should pass flex credentials to the service."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service:
            mock_service.import_snapshot.return_value = {
                "status": "completed",
                "source_type": "synthetic",
                "positions_imported": 0,
            }

            client.post("/api/brokers/ibkr/snapshot/1", headers=auth_headers)

            mock_service.import_snapshot.assert_called_once()
            call_args = mock_service.import_snapshot.call_args
            # Verify flex_token and flex_query_id were passed (positional args)
            assert call_args[0][2] == "test_token"
            assert call_args[0][3] == "test_query_id"

    def test_snapshot_endpoint_returns_500_on_failure(self, client_with_user, auth_headers):
        """Snapshot endpoint should return 500 when service reports failure."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service:
            mock_service.import_snapshot.return_value = {
                "status": "failed",
                "errors": ["Failed to fetch Flex Query report"],
            }

            response = client.post("/api/brokers/ibkr/snapshot/1", headers=auth_headers)

        assert response.status_code == 500
        data = response.json()
        assert "Snapshot import failed" in data["detail"]

    def test_snapshot_endpoint_requires_auth(self, client_with_user):
        """Snapshot endpoint should require authentication."""
        client, _ = client_with_user
        response = client.post("/api/brokers/ibkr/snapshot/1")
        assert response.status_code in [401, 403]

    def test_snapshot_endpoint_returns_404_for_nonexistent_account(
        self, client_with_user, auth_headers
    ):
        """Snapshot endpoint should return 404 for non-existent account."""
        client, _ = client_with_user
        response = client.post("/api/brokers/ibkr/snapshot/9999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_snapshot_endpoint_updates_last_import(self, client_with_user, auth_headers):
        """Snapshot endpoint should update last_import timestamp on success."""
        client, _ = client_with_user

        with (
            patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service,
            patch("app.routers.brokers._update_last_import") as mock_update,
        ):
            mock_service.import_snapshot.return_value = {
                "status": "completed",
                "source_type": "synthetic",
                "positions_imported": 1,
            }

            client.post("/api/brokers/ibkr/snapshot/1", headers=auth_headers)

            mock_update.assert_called_once()

    def test_snapshot_endpoint_includes_message(self, client_with_user, auth_headers):
        """Response should include a human-readable message."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service:
            mock_service.import_snapshot.return_value = {
                "status": "completed",
                "source_type": "synthetic",
                "positions_imported": 5,
            }

            response = client.post("/api/brokers/ibkr/snapshot/1", headers=auth_headers)

        data = response.json()
        assert "message" in data
        assert "Synthetic snapshot" in data["message"]
        assert "Test IBKR" in data["message"]


class TestSnapshotEndpointWithoutCredentials:
    """Test snapshot endpoint when account has no IBKR credentials."""

    @pytest.fixture
    def client_no_creds(self, test_db):
        """Create test client with account that has no IBKR credentials."""
        testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_db)

        db = testing_session_local()
        user = User(
            email="nocreds@example.com",
            password_hash=AuthService.hash_password("test123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        portfolio = Portfolio(user_id=user.id, name="Test Portfolio")
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

        # Create account WITHOUT ibkr credentials
        with test_db.connect() as conn:
            metadata = json.dumps({})
            conn.execute(
                text("""
                INSERT INTO accounts (id, portfolio_id, name, account_type, currency, broker_type, metadata)
                VALUES (2, :portfolio_id, 'No Creds Account', 'Brokerage', 'USD', 'ibkr', :metadata)
            """),
                {"portfolio_id": portfolio.id, "metadata": metadata},
            )
            conn.execute(
                text("""
                INSERT INTO portfolio_accounts (portfolio_id, account_id)
                VALUES (:portfolio_id, 2)
            """),
                {"portfolio_id": portfolio.id},
            )
            conn.commit()

        user_id = user.id
        db.close()

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        token = AuthService.create_access_token(user_id)
        headers = {"Authorization": f"Bearer {token}"}

        with TestClient(app) as test_client:
            yield test_client, headers

        app.dependency_overrides.clear()

    def test_snapshot_returns_400_without_credentials(self, client_no_creds):
        """Should return 400 when account has no IBKR credentials configured."""
        client, headers = client_no_creds
        response = client.post("/api/brokers/ibkr/snapshot/2", headers=headers)
        assert response.status_code == 400
        assert "credentials" in response.json()["detail"].lower()
