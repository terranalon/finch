"""Tests for asset detail response schemas."""

from datetime import date, datetime
from decimal import Decimal

from app.schemas.asset_detail import AssetDetailResponse, DailyMetricsResponse


class TestDailyMetricsResponse:
    def test_from_orm_attributes(self) -> None:
        """DailyMetricsResponse should serialize from ORM-like object."""
        data = DailyMetricsResponse(
            date=date(2026, 2, 18),
            open=Decimal("234.80"),
            high=Decimal("238.10"),
            low=Decimal("234.15"),
            close=Decimal("237.42"),
            volume=52300000,
            market_cap=Decimal("3620000000000"),
            pe_ratio=Decimal("37.2"),
            forward_pe=Decimal("31.8"),
            eps=Decimal("6.38"),
        )
        assert data.close == Decimal("237.42")
        assert data.pe_ratio == Decimal("37.2")

    def test_nullable_fields_default_to_none(self) -> None:
        """All optional fields should default to None."""
        data = DailyMetricsResponse(date=date(2026, 2, 18))
        assert data.market_cap is None
        assert data.close is None
        assert data.volume is None


class TestAssetDetailResponse:
    def test_with_daily_metrics(self) -> None:
        """AssetDetailResponse should include nested daily_metrics."""
        metrics = DailyMetricsResponse(
            date=date(2026, 2, 18),
            open=Decimal("234.80"),
            high=Decimal("238.10"),
            low=Decimal("234.15"),
            close=Decimal("237.42"),
            volume=52300000,
        )
        detail = AssetDetailResponse(
            id=1,
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Stock",
            currency="USD",
            is_favorite=True,
            category="Technology",
            industry="Consumer Electronics",
            description="Apple designs...",
            exchange="NASDAQ",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            daily_metrics=metrics,
        )
        assert detail.daily_metrics is not None
        assert detail.daily_metrics.close == Decimal("237.42")
        assert detail.exchange == "NASDAQ"

    def test_without_daily_metrics(self) -> None:
        """daily_metrics should be nullable (no data yet)."""
        detail = AssetDetailResponse(
            id=1,
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Stock",
            currency="USD",
            is_favorite=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            daily_metrics=None,
        )
        assert detail.daily_metrics is None
