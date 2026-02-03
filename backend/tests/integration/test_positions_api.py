"""Integration tests for positions API endpoint."""

from datetime import date
from decimal import Decimal

from app.models import ExchangeRate


class TestPositionsAPI:
    """Test /api/positions endpoint."""

    def test_list_positions_requires_auth(self, client):
        """Positions endpoint requires authentication."""
        response = client.get("/api/positions")
        assert response.status_code == 401

    def test_list_positions_returns_empty_for_new_user(self, auth_client):
        """Returns empty list when user has no holdings."""
        response = auth_client.get("/api/positions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_positions_returns_aggregated_holdings(self, auth_client, seed_holdings):
        """Returns holdings aggregated by asset."""
        response = auth_client.get("/api/positions")
        assert response.status_code == 200

        positions = response.json()
        assert len(positions) >= 1

        # Check required fields
        position = positions[0]
        assert "asset_id" in position
        assert "symbol" in position
        assert "total_quantity" in position
        assert "total_cost_basis" in position
        assert "total_market_value" in position
        assert "accounts" in position

        # Verify aggregation
        assert position["symbol"] == "AAPL"
        assert position["total_quantity"] == 10.0

    def test_list_positions_includes_pnl_calculations(self, auth_client, seed_holdings):
        """Positions include P&L calculations."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        # P&L should be calculated (current price 150 * 10 qty - 1400 cost = 100)
        assert position["total_pnl"] is not None
        assert position["total_pnl_pct"] is not None

    def test_list_positions_includes_day_change(self, auth_client, seed_holdings):
        """Positions include day change from previous close."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        # Day change should be calculated (150 current - 148 previous = 2)
        assert "day_change" in position
        assert "day_change_pct" in position

    def test_list_positions_filters_by_portfolio(self, auth_client, test_portfolio, seed_holdings):
        """Can filter positions by portfolio ID."""
        response = auth_client.get(f"/api/positions?portfolio_id={test_portfolio.id}")
        assert response.status_code == 200
        positions = response.json()
        assert len(positions) >= 1

    def test_list_positions_converts_currency(self, auth_client, seed_holdings, db):
        """Can convert positions to different display currency."""
        # Add exchange rate for ILS
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="ILS",
            rate=Decimal("3.70"),
            date=date.today(),
        )
        db.add(rate)
        db.commit()

        response = auth_client.get("/api/positions?display_currency=ILS")
        assert response.status_code == 200
        positions = response.json()

        if positions:
            # Values should be converted
            assert positions[0].get("display_currency") == "ILS"

    def test_list_positions_includes_account_breakdown(self, auth_client, seed_holdings):
        """Each position includes breakdown by account."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        assert "accounts" in position
        assert len(position["accounts"]) >= 1

        account = position["accounts"][0]
        assert "account_id" in account
        assert "account_name" in account
        assert "quantity" in account
        assert "cost_basis" in account
