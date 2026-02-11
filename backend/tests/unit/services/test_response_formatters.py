"""Tests for response formatters - pure functions, no DB needed."""

from decimal import Decimal

from app.services.portfolio.types import AccountHolding, PositionResult
from app.services.shared.response_formatters import (
    format_account_holding,
    format_position,
    to_float,
)


class TestToFloat:
    def test_decimal_to_float(self):
        assert to_float(Decimal("123.45")) == 123.45

    def test_none_returns_none(self):
        assert to_float(None) is None

    def test_zero(self):
        assert to_float(Decimal("0")) == 0.0


class TestFormatAccountHolding:
    def test_formats_all_fields(self):
        a = AccountHolding(
            holding_id=1,
            account_id=2,
            account_name="Test",
            account_type="brokerage",
            institution="Broker",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1000"),
            market_value_native=Decimal("1500"),
            pnl_native=Decimal("500"),
            cost_basis_usd=Decimal("1000"),
            market_value_usd=Decimal("1500"),
            pnl_usd=Decimal("500"),
            pnl_pct=Decimal("50"),
            strategy_horizon="long",
        )
        result = format_account_holding(a)
        assert result["holding_id"] == 1
        assert result["quantity"] == 10.0
        assert result["market_value"] == 1500.0


class TestFormatPosition:
    def test_formats_with_accounts(self):
        p = PositionResult(
            asset_id=1,
            symbol="AAPL",
            name="Apple",
            asset_class="Equity",
            category="Tech",
            industry="Consumer Electronics",
            currency="USD",
            is_favorite=False,
            current_price=Decimal("150"),
            previous_close_price=Decimal("148"),
            day_change=Decimal("2"),
            day_change_pct=Decimal("1.35"),
            day_change_date="2024-06-15",
            is_market_closed=False,
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_market_value_native=Decimal("1500"),
            total_pnl_native=Decimal("100"),
            avg_cost_per_unit_native=Decimal("140"),
            total_cost_basis_usd=Decimal("1400"),
            total_market_value_usd=Decimal("1500"),
            total_pnl_usd=Decimal("100"),
            total_pnl_pct=Decimal("7.14"),
            avg_cost_per_unit_usd=Decimal("140"),
            accounts=[],
        )
        result = format_position(p)
        assert result["symbol"] == "AAPL"
        assert result["current_price"] == 150.0
        assert result["account_count"] == 0
