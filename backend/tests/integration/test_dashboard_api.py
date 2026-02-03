"""Integration tests for dashboard API endpoint."""


class TestDashboardAPI:
    """Test /api/dashboard endpoints."""

    def test_dashboard_summary_requires_auth(self, client):
        """Dashboard endpoint requires authentication."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 401

    def test_dashboard_summary_returns_structure(self, auth_client):
        """Returns expected dashboard structure."""
        response = auth_client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = response.json()
        assert "total_value" in data
        assert "display_currency" in data
        assert "accounts" in data
        assert "asset_allocation" in data
        assert "top_holdings" in data
        assert "historical_performance" in data

    def test_dashboard_summary_with_holdings(self, auth_client, seed_holdings):
        """Dashboard shows correct totals with holdings."""
        response = auth_client.get("/api/dashboard/summary")
        data = response.json()

        # Should have positive total value
        assert data["total_value"] > 0

        # Should have accounts
        assert len(data["accounts"]) >= 1

        # Should have asset allocation
        assert len(data["asset_allocation"]) >= 1

    def test_dashboard_summary_filters_by_portfolio(
        self, auth_client, test_portfolio, seed_holdings
    ):
        """Can filter dashboard by portfolio."""
        response = auth_client.get(f"/api/dashboard/summary?portfolio_id={test_portfolio.id}")
        assert response.status_code == 200

    def test_dashboard_summary_converts_currency(self, auth_client, seed_holdings):
        """Can convert dashboard values to different currency."""
        response = auth_client.get("/api/dashboard/summary?display_currency=ILS")
        assert response.status_code == 200
        data = response.json()
        assert data["display_currency"] == "ILS"

    def test_benchmark_returns_data(self, auth_client):
        """Benchmark endpoint returns historical data."""
        response = auth_client.get("/api/dashboard/benchmark?symbol=SPY&period=1mo")
        assert response.status_code == 200

        data = response.json()
        assert "symbol" in data
        assert "data" in data
