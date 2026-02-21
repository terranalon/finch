"""Tests for Mizrahi Tefahot broker parser."""

from app.services.brokers.mizrahi.constants import (
    ACTION_TYPE_MAP,
    CURRENCY_CODE_MAP,
)


class TestConstants:
    """Test constant mappings."""

    def test_action_type_map_buy(self):
        assert ACTION_TYPE_MAP["קניה"] == "Buy"
        assert ACTION_TYPE_MAP["קניה רצף"] == "Buy"

    def test_action_type_map_buy_double_space(self):
        """Mizrahi files sometimes have double spaces in action types."""
        assert ACTION_TYPE_MAP["קניה  רצף"] == "Buy"

    def test_action_type_map_sell(self):
        assert ACTION_TYPE_MAP["מכירה"] == "Sell"
        assert ACTION_TYPE_MAP["מכירה רצף"] == "Sell"

    def test_action_type_map_sell_double_space(self):
        assert ACTION_TYPE_MAP["מכירה  רצף"] == "Sell"

    def test_action_type_map_special_types(self):
        assert ACTION_TYPE_MAP["הטבה"] == "Buy"
        assert ACTION_TYPE_MAP["פדיון"] == "Sell"
        assert ACTION_TYPE_MAP["החלפה/גריעה"] == "Sell"

    def test_currency_code_map(self):
        assert CURRENCY_CODE_MAP["000"] == "ILS"
        assert CURRENCY_CODE_MAP["001"] == "USD"
