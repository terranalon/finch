"""Unit tests for PriceFetcher.refresh_if_stale cooldown logic."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models import Asset
from app.services.market_data.price_fetcher import PriceFetcher


def _make_asset(
    last_fetched_price: Decimal | None = Decimal("150.00"),
    last_fetched_at: datetime | None = None,
    symbol: str = "AAPL",
    asset_class: str = "Stock",
) -> Asset:
    asset = MagicMock(spec=Asset)
    asset.symbol = symbol
    asset.asset_class = asset_class
    asset.last_fetched_price = last_fetched_price
    asset.last_fetched_at = last_fetched_at
    return asset


def test_refresh_if_stale_never_fetched_triggers_fetch():
    """When last_fetched_at is None, always fetch regardless of cooldown."""
    asset = _make_asset(last_fetched_at=None)
    db = MagicMock()

    with patch.object(PriceFetcher, "update_asset_price", return_value=True) as mock_fetch:
        refreshed, price, fetched_at = PriceFetcher.refresh_if_stale(db, asset)

    mock_fetch.assert_called_once_with(db, asset)
    assert refreshed is True


def test_refresh_if_stale_within_cooldown_skips_fetch():
    """When last_fetched_at is recent (within 60s), return cached values without fetching."""
    recent_time = datetime.now() - timedelta(seconds=30)
    cached_price = Decimal("155.00")
    asset = _make_asset(last_fetched_price=cached_price, last_fetched_at=recent_time)
    db = MagicMock()

    with patch.object(PriceFetcher, "update_asset_price") as mock_fetch:
        refreshed, price, fetched_at = PriceFetcher.refresh_if_stale(db, asset)

    mock_fetch.assert_not_called()
    assert refreshed is False
    assert price == cached_price
    assert fetched_at == recent_time


def test_refresh_if_stale_outside_cooldown_triggers_fetch():
    """When last_fetched_at is older than cooldown (60s), fetch a fresh price."""
    stale_time = datetime.now() - timedelta(seconds=90)
    asset = _make_asset(last_fetched_at=stale_time)
    db = MagicMock()

    # Simulate the fetch mutating the asset (as update_asset_price does)
    new_price = Decimal("160.00")
    new_time = datetime.now()

    def _fake_update(db, asset):
        asset.last_fetched_price = new_price
        asset.last_fetched_at = new_time
        return True

    with patch.object(PriceFetcher, "update_asset_price", side_effect=_fake_update):
        refreshed, price, fetched_at = PriceFetcher.refresh_if_stale(db, asset)

    assert refreshed is True
    assert price == new_price
    assert fetched_at == new_time


def test_refresh_if_stale_fetch_failure_returns_none_price():
    """When fetch is attempted but fails, return (True, None, None)."""
    stale_time = datetime.now() - timedelta(seconds=90)
    asset = _make_asset(last_fetched_at=stale_time)
    db = MagicMock()

    with patch.object(PriceFetcher, "update_asset_price", return_value=False):
        refreshed, price, fetched_at = PriceFetcher.refresh_if_stale(db, asset)

    assert refreshed is True
    assert price is None
    assert fetched_at is None


def test_refresh_if_stale_custom_cooldown():
    """Custom cooldown_seconds parameter is respected."""
    # 10 seconds old, default 60s cooldown → cached; custom 5s cooldown → fetch
    slightly_old = datetime.now() - timedelta(seconds=10)
    asset = _make_asset(last_fetched_at=slightly_old)
    db = MagicMock()

    with patch.object(PriceFetcher, "update_asset_price", return_value=True) as mock_fetch:
        refreshed, _, _ = PriceFetcher.refresh_if_stale(db, asset, cooldown_seconds=5)

    mock_fetch.assert_called_once()
    assert refreshed is True


def test_refresh_if_stale_exactly_at_cooldown_boundary_skips():
    """A price fetched exactly at the cooldown boundary is still considered fresh."""
    # 59 seconds old with default 60s cooldown → still within cooldown
    just_within = datetime.now() - timedelta(seconds=59)
    asset = _make_asset(last_fetched_at=just_within)
    db = MagicMock()

    with patch.object(PriceFetcher, "update_asset_price") as mock_fetch:
        refreshed, _, _ = PriceFetcher.refresh_if_stale(db, asset)

    mock_fetch.assert_not_called()
    assert refreshed is False
