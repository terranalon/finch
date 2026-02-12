"""Tests for position schemas."""

from decimal import Decimal

from app.schemas.position import PositionAccountDetail, PositionResponse


class TestPositionAccountDetail:
    """Tests for PositionAccountDetail schema."""

    def test_minimal_fields(self):
        """Create with only required fields."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1400"),
            cost_basis=Decimal("1400"),
        )
        assert account_detail.holding_id == 1
        assert account_detail.account_id == 1
        assert account_detail.account_name == "Test Account"
        assert account_detail.quantity == Decimal("10")
        assert account_detail.cost_basis_native == Decimal("1400")
        assert account_detail.cost_basis == Decimal("1400")

    def test_all_fields(self):
        """Create with all fields populated."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            account_type="brokerage",
            institution="Test Broker",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1400"),
            market_value_native=Decimal("1500"),
            pnl_native=Decimal("100"),
            cost_basis=Decimal("1400"),
            market_value=Decimal("1500"),
            pnl=Decimal("100"),
            pnl_pct=Decimal("7.14"),
            strategy_horizon="LongTerm",
        )
        assert account_detail.account_type == "brokerage"
        assert account_detail.institution == "Test Broker"
        assert account_detail.market_value_native == Decimal("1500")
        assert account_detail.pnl_native == Decimal("100")
        assert account_detail.market_value == Decimal("1500")
        assert account_detail.pnl == Decimal("100")
        assert account_detail.pnl_pct == Decimal("7.14")
        assert account_detail.strategy_horizon == "LongTerm"

    def test_optional_fields_default_to_none(self):
        """Optional fields default to None when not provided."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1400"),
            cost_basis=Decimal("1400"),
        )
        assert account_detail.account_type is None
        assert account_detail.institution is None
        assert account_detail.market_value_native is None
        assert account_detail.pnl_native is None
        assert account_detail.market_value is None
        assert account_detail.pnl is None
        assert account_detail.pnl_pct is None
        assert account_detail.strategy_horizon is None

    def test_serialization(self):
        """Schema serializes correctly to dict."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1400"),
            cost_basis=Decimal("1400"),
            pnl=Decimal("100"),
        )
        data = account_detail.model_dump()
        assert data["holding_id"] == 1
        assert data["account_name"] == "Test Account"
        assert data["pnl"] == Decimal("100")
        assert "cost_basis_native" in data


class TestPositionResponse:
    """Tests for PositionResponse schema."""

    def test_minimal_fields(self):
        """Create with only required fields."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
        )
        assert position.asset_id == 1
        assert position.symbol == "AAPL"
        assert position.total_quantity == Decimal("10")
        assert position.total_cost_basis_native == Decimal("1400")
        assert position.total_cost_basis == Decimal("1400")

    def test_all_fields(self):
        """Create with all fields populated."""
        account = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=Decimal("10"),
            cost_basis_native=Decimal("1400"),
            cost_basis=Decimal("1400"),
        )
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Equity",
            category="Technology",
            industry="Consumer Electronics",
            currency="USD",
            is_favorite=True,
            current_price=Decimal("150"),
            current_price_display=Decimal("150"),
            previous_close_price=Decimal("148"),
            day_change=Decimal("2"),
            day_change_pct=Decimal("1.35"),
            day_change_date="2026-02-03",
            is_market_closed=False,
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_market_value_native=Decimal("1500"),
            total_pnl_native=Decimal("100"),
            avg_cost_per_unit_native=Decimal("140"),
            total_cost_basis=Decimal("1400"),
            total_market_value=Decimal("1500"),
            current_value=Decimal("1500"),
            total_pnl=Decimal("100"),
            total_pnl_pct=Decimal("7.14"),
            avg_cost_per_unit=Decimal("140"),
            display_currency="USD",
            account_count=1,
            accounts=[account],
        )
        assert position.name == "Apple Inc."
        assert position.asset_class == "Equity"
        assert position.category == "Technology"
        assert position.industry == "Consumer Electronics"
        assert position.is_favorite is True
        assert position.current_price == Decimal("150")
        assert position.day_change == Decimal("2")
        assert position.day_change_pct == Decimal("1.35")
        assert position.total_market_value == Decimal("1500")
        assert position.total_pnl == Decimal("100")
        assert position.total_pnl_pct == Decimal("7.14")
        assert position.account_count == 1
        assert len(position.accounts) == 1

    def test_default_values(self):
        """Default values are set correctly."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
        )
        assert position.name is None
        assert position.asset_class is None
        assert position.currency == "USD"
        assert position.is_favorite is False
        assert position.is_market_closed is False
        assert position.avg_cost_per_unit_native == Decimal("0")
        assert position.avg_cost_per_unit == Decimal("0")
        assert position.display_currency == "USD"
        assert position.account_count == 0
        assert position.accounts == []

    def test_with_multiple_accounts(self):
        """Position with holdings from multiple accounts."""
        account1 = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Account A",
            quantity=Decimal("5"),
            cost_basis_native=Decimal("700"),
            cost_basis=Decimal("700"),
        )
        account2 = PositionAccountDetail(
            holding_id=2,
            account_id=2,
            account_name="Account B",
            quantity=Decimal("5"),
            cost_basis_native=Decimal("700"),
            cost_basis=Decimal("700"),
        )
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
            account_count=2,
            accounts=[account1, account2],
        )
        assert position.account_count == 2
        assert len(position.accounts) == 2
        assert position.accounts[0].account_name == "Account A"
        assert position.accounts[1].account_name == "Account B"

    def test_serialization(self):
        """Schema serializes correctly to dict."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            name="Apple Inc.",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
            total_pnl=Decimal("100"),
            accounts=[],
        )
        data = position.model_dump()
        assert data["asset_id"] == 1
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["total_pnl"] == Decimal("100")
        assert "accounts" in data
        assert isinstance(data["accounts"], list)

    def test_current_value_alias(self):
        """current_value is an alias for total_market_value."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
            total_market_value=Decimal("1500"),
            current_value=Decimal("1500"),
        )
        assert position.current_value == Decimal("1500")
        assert position.total_market_value == Decimal("1500")

    def test_pnl_calculations_nullable(self):
        """P&L fields can be null when price data unavailable."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=Decimal("10"),
            total_cost_basis_native=Decimal("1400"),
            total_cost_basis=Decimal("1400"),
            total_market_value=None,
            total_pnl=None,
            total_pnl_pct=None,
        )
        assert position.total_market_value is None
        assert position.total_pnl is None
        assert position.total_pnl_pct is None
