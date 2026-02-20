"""Integration tests for PATCH /api/assets/{asset_id}/price endpoint."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

PATCH_TARGET = "app.routers.assets.PriceFetcher.refresh_if_stale"


def test_refresh_price_returns_correct_fields_when_refreshed(client, test_asset):
    """Endpoint returns last_fetched_price and last_fetched_at when a fresh fetch occurs."""
    fetched_at = datetime(2026, 2, 20, 12, 0, 0)
    mock_result = (True, Decimal("175.50"), fetched_at)

    with patch(PATCH_TARGET, return_value=mock_result):
        res = client.patch(f"/api/assets/{test_asset.id}/price")

    assert res.status_code == 200
    data = res.json()
    assert data["refreshed"] is True
    assert data["last_fetched_price"] == pytest.approx(175.50)
    assert data["last_fetched_at"] == "2026-02-20T12:00:00"
    assert data["asset_id"] == test_asset.id
    assert data["symbol"] == test_asset.symbol


def test_refresh_price_returns_cached_when_within_cooldown(client, test_asset):
    """Endpoint returns refreshed=False and cached values when cooldown is active."""
    cached_at = datetime(2026, 2, 20, 11, 59, 30)
    mock_result = (False, Decimal("150.00"), cached_at)

    with patch(PATCH_TARGET, return_value=mock_result):
        res = client.patch(f"/api/assets/{test_asset.id}/price")

    assert res.status_code == 200
    data = res.json()
    assert data["refreshed"] is False
    assert data["last_fetched_price"] == pytest.approx(150.00)
    assert data["last_fetched_at"] == "2026-02-20T11:59:30"


def test_refresh_price_404_for_unknown_asset(client):
    """Endpoint returns 404 when the asset does not exist."""
    res = client.patch("/api/assets/99999/price")
    assert res.status_code == 404


def test_refresh_price_400_for_asset_without_symbol(client, db):
    """Endpoint returns 400 when the asset has an empty symbol (e.g. a Cash asset)."""
    from app.models import Asset

    # symbol is NOT NULL in the DB schema; use empty string to trigger the
    # `if not asset.symbol` guard without violating the DB constraint
    cash_asset = Asset(
        symbol="",
        name="USD Cash",
        asset_class="Cash",
        currency="USD",
    )
    db.add(cash_asset)
    db.commit()
    db.refresh(cash_asset)

    res = client.patch(f"/api/assets/{cash_asset.id}/price")
    assert res.status_code == 400


def test_refresh_price_500_when_fetch_fails(client, test_asset):
    """Endpoint returns 500 when a fresh fetch was attempted but the provider returned nothing."""
    mock_result = (True, None, None)

    with patch(PATCH_TARGET, return_value=mock_result):
        res = client.patch(f"/api/assets/{test_asset.id}/price")

    assert res.status_code == 500
