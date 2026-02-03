"""Integration tests for auth API endpoints.

These are critical for Airflow DAG authentication.
"""


class TestAuthAPI:
    """Test /api/auth endpoints."""

    def test_login_with_valid_credentials(self, client, test_user):
        """Login returns tokens with valid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_password(self, client, test_user):
        """Login fails with invalid password."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_with_nonexistent_user(self, client):
        """Login fails with nonexistent user."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "password"},
        )
        assert response.status_code == 401

    def test_access_token_grants_access(self, client, test_user):
        """Access token can be used to access protected endpoints."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/portfolios",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_refresh_token_flow(self, client, test_user):
        """Can refresh access token using refresh token."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
