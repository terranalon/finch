"""Integration tests for GET /api/dashboard/movers."""

from datetime import date, timedelta
from decimal import Decimal

from app.models import AssetPrice


class TestDashboardMovers:
    """Test /api/dashboard/movers endpoint."""

    def test_movers_requires_auth(self, client):
        response = client.get("/api/dashboard/movers")
        assert response.status_code == 401

    def test_movers_empty_portfolio(self, auth_client):
        response = auth_client.get("/api/dashboard/movers")
        assert response.status_code == 200
        data = response.json()
        assert data["gainers"] == []
        assert data["losers"] == []

    def test_movers_returns_sorted_gainers_and_losers(
        self, auth_client, db, test_account, test_portfolio
    ):
        """With multiple assets having day changes, returns sorted gainers/losers."""
        from app.models import Asset, Holding

        yesterday = date.today() - timedelta(days=1)

        # Create 4 assets with different day changes
        assets_data = [
            ("AAPL", "Apple", Decimal("150.00"), Decimal("145.00")),  # +3.45%
            ("GOOGL", "Google", Decimal("100.00"), Decimal("105.00")),  # -4.76%
            ("MSFT", "Microsoft", Decimal("200.00"), Decimal("190.00")),  # +5.26%
            ("TSLA", "Tesla", Decimal("180.00"), Decimal("200.00")),  # -10.00%
        ]

        for symbol, name, current, prev_close in assets_data:
            asset = Asset(
                symbol=symbol,
                name=name,
                asset_class="Equity",
                currency="USD",
                last_fetched_price=current,
            )
            db.add(asset)
            db.flush()

            holding = Holding(
                account_id=test_account.id,
                asset_id=asset.id,
                quantity=Decimal("10"),
                cost_basis=Decimal("1000"),
                is_active=True,
            )
            db.add(holding)

            price = AssetPrice(
                asset_id=asset.id,
                date=yesterday,
                closing_price=prev_close,
                currency="USD",
            )
            db.add(price)

        db.commit()

        response = auth_client.get("/api/dashboard/movers?limit=2")
        assert response.status_code == 200
        data = response.json()

        assert len(data["gainers"]) <= 2
        assert len(data["losers"]) <= 2

        # Gainers should be sorted by day_change_pct descending
        if len(data["gainers"]) >= 2:
            assert data["gainers"][0]["day_change_pct"] >= data["gainers"][1]["day_change_pct"]

        # Losers should be sorted by day_change_pct ascending (most negative first)
        if len(data["losers"]) >= 2:
            assert data["losers"][0]["day_change_pct"] <= data["losers"][1]["day_change_pct"]

    def test_movers_respects_limit(self, auth_client, seed_holdings):
        response = auth_client.get("/api/dashboard/movers?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["gainers"]) <= 1
        assert len(data["losers"]) <= 1

    def test_movers_filters_by_portfolio(self, auth_client, test_portfolio, seed_holdings):
        response = auth_client.get(f"/api/dashboard/movers?portfolio_id={test_portfolio.id}")
        assert response.status_code == 200

    def test_movers_response_shape(self, auth_client, seed_holdings):
        response = auth_client.get("/api/dashboard/movers")
        data = response.json()

        assert "gainers" in data
        assert "losers" in data

        # Check field presence on any returned mover
        for mover_list in [data["gainers"], data["losers"]]:
            for mover in mover_list:
                assert "asset_id" in mover
                assert "symbol" in mover
                assert "name" in mover
                assert "current_price" in mover
                assert "day_change_pct" in mover
                assert "currency" in mover
