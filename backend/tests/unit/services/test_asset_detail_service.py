"""Tests for AssetDetailService."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models import Asset
from app.models.asset_daily_metrics import AssetDailyMetrics
from app.services.asset_detail_service import AssetDetailService


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sample_asset() -> Asset:
    return Asset(
        id=1,
        symbol="AAPL",
        name="Apple Inc.",
        asset_class="Stock",
        currency="USD",
        is_favorite=True,
        description="Apple designs...",
        exchange="NASDAQ",
        beta=Decimal("1.24"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_metrics() -> AssetDailyMetrics:
    return AssetDailyMetrics(
        id=1,
        asset_id=1,
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


class TestAssetDetailService:
    def test_get_asset_detail_with_metrics(
        self, mock_db: MagicMock, sample_asset: Asset, sample_metrics: AssetDailyMetrics
    ) -> None:
        """Should return asset with nested daily_metrics."""
        mock_db.get.return_value = sample_asset
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_metrics

        result = AssetDetailService.get_asset_detail(mock_db, asset_id=1)

        assert result.symbol == "AAPL"
        assert result.daily_metrics is not None
        assert result.daily_metrics.close == Decimal("237.42")

    def test_get_asset_detail_without_metrics(
        self, mock_db: MagicMock, sample_asset: Asset
    ) -> None:
        """Should return asset with daily_metrics=None when no data exists."""
        mock_db.get.return_value = sample_asset
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = AssetDetailService.get_asset_detail(mock_db, asset_id=1)

        assert result.symbol == "AAPL"
        assert result.daily_metrics is None

    def test_get_asset_detail_not_found(self, mock_db: MagicMock) -> None:
        """Should raise NotFoundError when asset doesn't exist."""
        mock_db.get.return_value = None

        with pytest.raises(Exception, match="not found"):
            AssetDetailService.get_asset_detail(mock_db, asset_id=999)
