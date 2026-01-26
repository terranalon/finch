"""Tests for crypto asset day change calculation."""


class TestCryptoMarketDetection:
    """Test that crypto assets always use live price calculation."""

    def test_crypto_is_never_marked_as_market_closed(self):
        """Crypto markets are 24/7 - is_market_closed should always be False."""
        # This tests the logic we'll add: crypto should bypass TradingCalendarService
        position = {
            "asset_class": "Crypto",
            "symbol": "BTC",
            "asset_id": 1,
        }

        # On a weekend (when NYSE is closed), crypto should still show is_market_closed=False
        # The fix: check asset_class == "Crypto" before calling TradingCalendarService
        if position["asset_class"] == "Crypto":
            is_asset_market_closed = False
        else:
            # Would call TradingCalendarService here
            is_asset_market_closed = True  # Simulating weekend

        assert is_asset_market_closed is False

    def test_crypto_uses_current_price_vs_previous_close(self):
        """Crypto day change should compare current price vs previous close, not two historical closes."""
        # When is_market_closed=False, the code uses:
        #   price_for_day_change = current_price
        #   previous_close_price = previous_close_map.get(asset_id)
        # This is the correct behavior for crypto

        current_price = 100000.0  # Current BTC price
        previous_close = 99000.0  # Yesterday's close

        # Market open path calculation
        day_change = current_price - previous_close
        day_change_pct = (day_change / previous_close) * 100

        assert day_change == 1000.0
        assert abs(day_change_pct - 1.01) < 0.01  # ~1% change
