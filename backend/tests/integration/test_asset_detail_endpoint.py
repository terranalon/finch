"""Integration tests for GET /api/assets/{asset_id}/detail."""

from datetime import date
from decimal import Decimal

from app.models import Asset, AssetDailyMetrics


class TestGetAssetDetail:
    def test_returns_asset_with_daily_metrics(self, auth_client, db) -> None:
        """Should return full asset detail with nested daily_metrics."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Stock",
            currency="USD",
            description="Apple designs...",
            exchange="NASDAQ",
            beta=Decimal("1.24"),
        )
        db.add(asset)
        db.flush()

        metrics = AssetDailyMetrics(
            asset_id=asset.id,
            date=date(2026, 2, 18),
            open=Decimal("234.80"),
            high=Decimal("238.10"),
            low=Decimal("234.15"),
            close=Decimal("237.42"),
            volume=52300000,
            market_cap=Decimal("3620000000000"),
            pe_ratio=Decimal("37.2"),
            source="Yahoo Finance",
        )
        db.add(metrics)
        db.commit()

        response = auth_client.get(f"/api/assets/{asset.id}/detail")
        assert response.status_code == 200

        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["exchange"] == "NASDAQ"
        assert data["description"] == "Apple designs..."
        assert data["daily_metrics"]["close"] == "237.4200"
        assert data["daily_metrics"]["pe_ratio"] == "37.2000"
        assert data["daily_metrics"]["date"] == "2026-02-18"

    def test_returns_asset_without_daily_metrics(self, auth_client, db) -> None:
        """Should return asset with daily_metrics=null when no data."""
        asset = Asset(
            symbol="NEW",
            name="New Asset",
            asset_class="Stock",
            currency="USD",
        )
        db.add(asset)
        db.commit()

        response = auth_client.get(f"/api/assets/{asset.id}/detail")
        assert response.status_code == 200

        data = response.json()
        assert data["symbol"] == "NEW"
        assert data["daily_metrics"] is None

    def test_returns_latest_metrics(self, auth_client, db) -> None:
        """Should return the most recent daily_metrics row."""
        asset = Asset(
            symbol="MSFT",
            name="Microsoft",
            asset_class="Stock",
            currency="USD",
        )
        db.add(asset)
        db.flush()

        old = AssetDailyMetrics(
            asset_id=asset.id,
            date=date(2026, 2, 17),
            close=Decimal("400.00"),
            source="Yahoo Finance",
        )
        new = AssetDailyMetrics(
            asset_id=asset.id,
            date=date(2026, 2, 18),
            close=Decimal("410.00"),
            source="Yahoo Finance",
        )
        db.add_all([old, new])
        db.commit()

        response = auth_client.get(f"/api/assets/{asset.id}/detail")
        data = response.json()
        assert data["daily_metrics"]["close"] == "410.0000"
        assert data["daily_metrics"]["date"] == "2026-02-18"

    def test_asset_not_found(self, auth_client) -> None:
        """Should return 404 for non-existent asset."""
        response = auth_client.get("/api/assets/99999/detail")
        assert response.status_code == 404

    def test_requires_auth(self, client) -> None:
        """Should return 401 without authentication."""
        response = client.get("/api/assets/1/detail")
        assert response.status_code == 401
