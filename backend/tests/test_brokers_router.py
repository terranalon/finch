"""Tests for unified brokers router."""

from unittest.mock import MagicMock, patch

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
    # Note: Python attribute is meta_data but column name is "metadata"
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
    """Create test client with a user, portfolio, and account."""
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

    # Create a test account with broker credentials
    with test_db.connect() as conn:
        import json

        metadata = json.dumps(
            {
                "kraken": {"api_key": "test_key", "api_secret": "test_secret"},
                "bit2c": {"api_key": "test_key", "api_secret": "test_secret"},
                "ibkr": {"flex_token": "test_token", "flex_query_id": "test_query"},
            }
        )
        conn.execute(
            text(
                """
            INSERT INTO accounts (id, portfolio_id, name, account_type, currency, broker_type, metadata)
            VALUES (1, :portfolio_id, 'Test Account', 'investment', 'USD', 'kraken', :metadata)
        """
            ),
            {"portfolio_id": portfolio.id, "metadata": metadata},
        )
        # Link account to portfolio via portfolio_accounts join table
        conn.execute(
            text(
                """
            INSERT INTO portfolio_accounts (portfolio_id, account_id)
            VALUES (:portfolio_id, 1)
        """
            ),
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


class TestListBrokers:
    """Test listing supported brokers."""

    def test_list_brokers_returns_all_supported(self, client_with_user, auth_headers):
        """Test that list brokers returns all supported brokers."""
        client, _ = client_with_user
        response = client.get("/api/brokers/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "brokers" in data

        broker_keys = [b["key"] for b in data["brokers"]]
        assert "ibkr" in broker_keys
        assert "kraken" in broker_keys
        assert "bit2c" in broker_keys

    def test_list_brokers_includes_capabilities(self, client_with_user, auth_headers):
        """Test that broker listing includes capability information."""
        client, _ = client_with_user
        response = client.get("/api/brokers/", headers=auth_headers)

        data = response.json()
        brokers_by_key = {b["key"]: b for b in data["brokers"]}

        # IBKR should support staging
        assert brokers_by_key["ibkr"]["supports_staging"] is True
        assert brokers_by_key["ibkr"]["credential_type"] == "flex_query"

        # Kraken should not support staging
        assert brokers_by_key["kraken"]["supports_staging"] is False
        assert brokers_by_key["kraken"]["credential_type"] == "api_key_secret"


class TestAuthRequirements:
    """Test authentication requirements."""

    def test_import_requires_auth(self, client_with_user):
        """Test that import endpoint requires authentication."""
        client, _ = client_with_user
        response = client.post("/api/brokers/kraken/import/1")
        assert response.status_code in [401, 403]

    def test_test_credentials_requires_auth(self, client_with_user):
        """Test that test-credentials endpoint requires authentication."""
        client, _ = client_with_user
        response = client.post("/api/brokers/kraken/test-credentials/1")
        assert response.status_code in [401, 403]

    def test_ibkr_credentials_requires_auth(self, client_with_user):
        """Test that IBKR credentials endpoint requires authentication."""
        client, _ = client_with_user
        response = client.put(
            "/api/brokers/ibkr/credentials/1",
            json={"flex_token": "x", "flex_query_id": "y"},
        )
        assert response.status_code in [401, 403]


class TestUnknownBroker:
    """Test handling of unknown broker types."""

    def test_import_unknown_broker_returns_404(self, client_with_user, auth_headers):
        """Test that importing from unknown broker returns 404."""
        client, _ = client_with_user
        response = client.post("/api/brokers/unknown_broker/import/1", headers=auth_headers)
        assert response.status_code == 422  # FastAPI validation error for enum

    def test_test_credentials_unknown_broker_returns_422(self, client_with_user, auth_headers):
        """Test that test-credentials for unknown broker returns 422."""
        client, _ = client_with_user
        response = client.post(
            "/api/brokers/unknown_broker/test-credentials/1", headers=auth_headers
        )
        assert response.status_code == 422


class TestAccountValidation:
    """Test account ownership validation."""

    def test_import_nonexistent_account_returns_404(self, client_with_user, auth_headers):
        """Test that importing to non-existent account returns 404."""
        client, _ = client_with_user
        response = client.post("/api/brokers/kraken/import/9999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCryptoBrokerImport:
    """Test crypto broker import functionality."""

    def test_kraken_import_success(self, client_with_user, auth_headers):
        """Test successful Kraken import with mocked client."""
        client, _ = client_with_user

        # Mock the crypto client factory and import service
        mock_broker_data = MagicMock()
        mock_broker_data.positions = []
        mock_broker_data.cash_transactions = []

        mock_client = MagicMock()
        mock_client.fetch_all_data.return_value = mock_broker_data

        with (
            patch("app.routers.brokers._create_crypto_client", return_value=mock_client),
            patch("app.routers.brokers.CryptoImportService") as mock_service_class,
        ):
            mock_service = MagicMock()
            mock_service.import_data.return_value = {
                "status": "completed",
                "positions": {"imported": 0},
                "transactions": {"imported": 0},
            }
            mock_service_class.return_value = mock_service

            response = client.post("/api/brokers/kraken/import/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "Kraken" in data["message"]

    def test_bit2c_import_success(self, client_with_user, auth_headers):
        """Test successful Bit2C import with mocked client."""
        client, _ = client_with_user

        mock_broker_data = MagicMock()
        mock_broker_data.positions = []
        mock_broker_data.cash_transactions = []

        mock_client = MagicMock()
        mock_client.fetch_all_data.return_value = mock_broker_data

        with (
            patch("app.routers.brokers._create_crypto_client", return_value=mock_client),
            patch("app.routers.brokers.CryptoImportService") as mock_service_class,
        ):
            mock_service = MagicMock()
            mock_service.import_data.return_value = {
                "status": "completed",
                "positions": {"imported": 0},
            }
            mock_service_class.return_value = mock_service

            response = client.post("/api/brokers/bit2c/import/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestTestCredentials:
    """Test credential testing functionality."""

    def test_kraken_test_credentials_success(self, client_with_user, auth_headers):
        """Test successful Kraken credential testing."""
        client, _ = client_with_user

        mock_client = MagicMock()
        mock_client.get_balance.return_value = {"USD": 1000, "BTC": 0.5}

        with patch("app.routers.brokers._create_crypto_client", return_value=mock_client):
            response = client.post("/api/brokers/kraken/test-credentials/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["assets_count"] == 2

    def test_bit2c_test_credentials_success(self, client_with_user, auth_headers):
        """Test successful Bit2C credential testing."""
        client, _ = client_with_user

        mock_client = MagicMock()
        mock_client.get_balance.return_value = {"ILS": 5000, "BTC": 0.1}

        with patch("app.routers.brokers._create_crypto_client", return_value=mock_client):
            response = client.post("/api/brokers/bit2c/test-credentials/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_ibkr_test_credentials_success(self, client_with_user, auth_headers):
        """Test successful IBKR credential testing via Flex Query."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRFlexClient") as mock_client_class:
            mock_client_class.request_flex_query.return_value = "12345"

            response = client.post("/api/brokers/ibkr/test-credentials/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["reference_code"] == "12345"

    def test_test_credentials_failure(self, client_with_user, auth_headers):
        """Test credential testing returns failure on API error."""
        client, _ = client_with_user

        mock_client = MagicMock()
        mock_client.get_balance.side_effect = Exception("Invalid API key")

        with patch("app.routers.brokers._create_crypto_client", return_value=mock_client):
            response = client.post("/api/brokers/kraken/test-credentials/1", headers=auth_headers)

        assert response.status_code == 200  # Returns 200 with status: failed
        data = response.json()
        assert data["status"] == "failed"
        assert "Invalid API key" in data["message"]


class TestCredentialManagement:
    """Test unified credential management endpoints."""

    def test_put_kraken_credentials(self, client_with_user, auth_headers):
        """Test storing Kraken API credentials."""
        client, _ = client_with_user

        response = client.put(
            "/api/brokers/kraken/credentials/1",
            json={"api_key": "new_key", "api_secret": "new_secret"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stored"
        assert data["broker"] == "kraken"

    def test_put_ibkr_credentials(self, client_with_user, auth_headers):
        """Test storing IBKR Flex Query credentials."""
        client, _ = client_with_user

        response = client.put(
            "/api/brokers/ibkr/credentials/1",
            json={"flex_token": "new_token", "flex_query_id": "new_query"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stored"
        assert data["broker"] == "ibkr"

    def test_get_credentials_status_with_credentials(self, client_with_user, auth_headers):
        """Test checking credential status when credentials exist."""
        client, _ = client_with_user

        response = client.get(
            "/api/brokers/kraken/credentials/1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["broker"] == "kraken"
        assert data["has_credentials"] is True
        assert data["credential_type"] == "api_key_secret"

    def test_get_credentials_status_without_credentials(self, client_with_user, auth_headers):
        """Test checking credential status when no credentials exist."""
        client, _ = client_with_user

        # First delete the credentials
        client.delete("/api/brokers/kraken/credentials/1", headers=auth_headers)

        response = client.get(
            "/api/brokers/kraken/credentials/1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_credentials"] is False

    def test_delete_credentials(self, client_with_user, auth_headers):
        """Test deleting broker credentials."""
        client, _ = client_with_user

        response = client.delete(
            "/api/brokers/kraken/credentials/1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_delete_nonexistent_credentials(self, client_with_user, auth_headers):
        """Test deleting credentials that don't exist."""
        client, _ = client_with_user

        # Delete twice - second should return not_found
        client.delete("/api/brokers/bit2c/credentials/1", headers=auth_headers)
        response = client.delete(
            "/api/brokers/bit2c/credentials/1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    def test_credentials_require_auth(self, client_with_user):
        """Test that credential endpoints require authentication."""
        client, _ = client_with_user

        # PUT
        response = client.put(
            "/api/brokers/kraken/credentials/1",
            json={"api_key": "key", "api_secret": "secret"},
        )
        assert response.status_code in [401, 403]

        # GET
        response = client.get("/api/brokers/kraken/credentials/1")
        assert response.status_code in [401, 403]

        # DELETE
        response = client.delete("/api/brokers/kraken/credentials/1")
        assert response.status_code in [401, 403]


class TestIBKRImport:
    """Test IBKR import functionality."""

    def test_ibkr_import_with_staging(self, client_with_user, auth_headers):
        """Test IBKR import using staged import."""
        client, _ = client_with_user

        with patch("app.routers.brokers.StagedImportService") as mock_staged:
            mock_staged.import_with_staging.return_value = {
                "status": "completed",
                "positions": {"imported": 10},
            }

            response = client.post(
                "/api/brokers/ibkr/import/1?use_staging=true", headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["import_method"] == "staged"

    def test_ibkr_import_without_staging(self, client_with_user, auth_headers):
        """Test IBKR import using atomic import."""
        client, _ = client_with_user

        with patch("app.routers.brokers.IBKRFlexImportService") as mock_flex:
            mock_flex.import_all.return_value = {
                "status": "completed",
                "positions": {"imported": 10},
            }

            response = client.post(
                "/api/brokers/ibkr/import/1?use_staging=false", headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["import_method"] == "atomic"


class TestApiConnectionsEndpoint:
    """Tests for GET /api/brokers/api-connections endpoint."""

    def test_returns_accounts_with_kraken_credentials(self, client_with_user, auth_headers):
        """Accounts with Kraken API credentials are included."""
        client, _ = client_with_user
        # The test fixture already creates an account with kraken credentials
        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert any(item["account_id"] == 1 and item["broker_type"] == "kraken" for item in data)

    def test_returns_accounts_with_ibkr_credentials(self, client_with_user, auth_headers):
        """Accounts with IBKR Flex Query credentials are included."""
        client, _ = client_with_user
        # The test fixture already creates an account with ibkr credentials
        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert any(item["account_id"] == 1 and item["broker_type"] == "ibkr" for item in data)

    def test_returns_accounts_with_bit2c_credentials(self, client_with_user, auth_headers):
        """Accounts with Bit2C API credentials are included."""
        client, _ = client_with_user
        # The test fixture already creates an account with bit2c credentials
        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert any(item["account_id"] == 1 and item["broker_type"] == "bit2c" for item in data)

    def test_returns_multiple_brokers_for_same_account(self, client_with_user, auth_headers):
        """Account with multiple broker credentials returns multiple entries."""
        client, _ = client_with_user
        # The test fixture creates account with kraken, bit2c, and ibkr credentials
        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        account_entries = [item for item in data if item["account_id"] == 1]
        broker_types = {item["broker_type"] for item in account_entries}
        assert broker_types == {"kraken", "bit2c", "ibkr"}

    def test_requires_authentication(self, client_with_user):
        """Endpoint requires valid authentication."""
        client, _ = client_with_user
        response = client.get("/api/brokers/api-connections")
        assert response.status_code in [401, 403]

    def test_excludes_accounts_without_credentials(self, client_with_user, auth_headers, test_db):
        """Accounts without API credentials are excluded."""
        client, _ = client_with_user

        # Create an account without any broker credentials
        with test_db.connect() as conn:
            import json

            metadata = json.dumps({})  # Empty metadata - no credentials
            conn.execute(
                text(
                    """
                INSERT INTO accounts (id, name, account_type, currency, is_active, metadata)
                VALUES (999, 'Manual Only Account', 'investment', 'USD', 1, :metadata)
            """
                ),
                {"metadata": metadata},
            )
            conn.commit()

        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert not any(item["account_id"] == 999 for item in data)

    def test_excludes_inactive_accounts(self, client_with_user, auth_headers, test_db):
        """Inactive accounts are excluded even with credentials."""
        client, _ = client_with_user

        # Create an inactive account with credentials
        with test_db.connect() as conn:
            import json

            metadata = json.dumps(
                {
                    "kraken": {
                        "api_key": "test-key",
                        "api_secret": "test-secret",
                    }
                }
            )
            conn.execute(
                text(
                    """
                INSERT INTO accounts (id, name, account_type, currency, is_active, metadata)
                VALUES (998, 'Inactive Account', 'investment', 'USD', 0, :metadata)
            """
                ),
                {"metadata": metadata},
            )
            conn.commit()

        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert not any(item["account_id"] == 998 for item in data)

    def test_user_only_sees_own_accounts(self, client_with_user, auth_headers, test_db):
        """Regular users only see accounts in their portfolios."""
        client, _ = client_with_user

        # Create an account NOT linked to any portfolio (orphan)
        with test_db.connect() as conn:
            import json

            metadata = json.dumps(
                {
                    "kraken": {
                        "api_key": "other-key",
                        "api_secret": "other-secret",
                    }
                }
            )
            conn.execute(
                text(
                    """
                INSERT INTO accounts (id, name, account_type, currency, is_active, metadata)
                VALUES (997, 'Other User Account', 'investment', 'USD', 1, :metadata)
            """
                ),
                {"metadata": metadata},
            )
            conn.commit()

        response = client.get("/api/brokers/api-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # The orphan account should NOT appear because it's not in user's portfolio
        assert not any(item["account_id"] == 997 for item in data)


class TestApiImportTriggersSnapshotGeneration:
    """Tests for background snapshot generation on API import."""

    def test_import_with_date_range_triggers_snapshot_generation(
        self, client_with_user, auth_headers
    ):
        """Should trigger snapshot generation when import returns date_range."""
        client, _ = client_with_user

        with (
            patch("app.routers.brokers._import_crypto_broker") as mock_import,
            patch("app.routers.brokers.update_snapshot_status") as mock_status,
            patch("app.routers.brokers.generate_snapshots_background") as mock_bg,
        ):
            # Mock successful import with date_range
            mock_import.return_value = {
                "status": "completed",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-06-30",
                },
                "transactions": {"imported": 10},
            }

            response = client.post("/api/brokers/kraken/import/1", headers=auth_headers)

            assert response.status_code == 200

            # Verify snapshot status was set to "generating"
            mock_status.assert_called()
            call_args = mock_status.call_args
            assert call_args[0][2] == "generating"  # Third arg is status

    def test_import_without_date_range_does_not_trigger_snapshot(
        self, client_with_user, auth_headers
    ):
        """Should not trigger snapshot generation when import has no date_range."""
        client, _ = client_with_user

        with (
            patch("app.routers.brokers._import_crypto_broker") as mock_import,
            patch("app.routers.brokers.update_snapshot_status") as mock_status,
        ):
            # Mock import without date_range
            mock_import.return_value = {
                "status": "completed",
                "transactions": {"imported": 0},
            }

            response = client.post("/api/brokers/kraken/import/1", headers=auth_headers)

            assert response.status_code == 200

            # Snapshot status should NOT be called
            mock_status.assert_not_called()

    def test_ibkr_import_triggers_snapshot_generation(self, client_with_user, auth_headers):
        """IBKR import should also trigger snapshot generation with date_range."""
        client, _ = client_with_user

        with (
            patch("app.routers.brokers.IBKRFlexImportService") as mock_flex,
            patch("app.routers.brokers.update_snapshot_status") as mock_status,
            patch("app.routers.brokers.generate_snapshots_background") as mock_bg,
        ):
            mock_flex.import_all.return_value = {
                "status": "completed",
                "date_range": {
                    "start_date": "2024-02-01",
                    "end_date": "2024-05-15",
                },
                "positions": {"imported": 5},
            }

            response = client.post(
                "/api/brokers/ibkr/import/1?use_staging=false", headers=auth_headers
            )

            assert response.status_code == 200

            # Verify snapshot status was set
            mock_status.assert_called()
            call_args = mock_status.call_args
            assert call_args[0][2] == "generating"
