"""Helper service for API currency conversion."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.shared.currency_service import CurrencyService

logger = logging.getLogger(__name__)


class CurrencyConversionHelper:
    """Helper for converting API response values to requested display currency."""

    @staticmethod
    def convert_value(
        db: Session,
        value: Decimal | float,
        from_currency: str,
        to_currency: str,
        conversion_date: date | None = None,
    ) -> Decimal:
        """
        Convert a single value from one currency to another.

        Args:
            db: Database session
            value: Value to convert
            from_currency: Source currency code
            to_currency: Target currency code
            conversion_date: Date for exchange rate (default: today)

        Returns:
            Converted value as Decimal
        """
        if not conversion_date:
            conversion_date = date.today()

        # Convert to Decimal if needed
        if isinstance(value, float):
            value = Decimal(str(value))

        # Same currency - no conversion needed
        if from_currency == to_currency:
            return value

        # Get exchange rate
        rate = CurrencyService.get_exchange_rate(db, from_currency, to_currency, conversion_date)

        if rate:
            return value * rate
        else:
            logger.warning(
                f"No exchange rate for {from_currency}/{to_currency} on {conversion_date}, "
                f"returning original value"
            )
            return value

    @staticmethod
    def convert_position_dict(
        db: Session, position: dict, display_currency: str, conversion_date: date | None = None
    ) -> dict:
        """
        Convert position dictionary values to display currency.

        Args:
            db: Database session
            position: Position dict with currency-denominated values
            display_currency: Target currency
            conversion_date: Date for exchange rate (default: today)

        Returns:
            Position dict with converted values
        """
        # All monetary values in position are already in USD
        # (converted in the positions endpoint)
        # We just need to convert from USD to display currency
        native_currency = "USD"

        if native_currency == display_currency:
            # No conversion needed
            position["display_currency"] = display_currency
            return position

        # Convert monetary values (already in USD, convert to display currency)
        # Note: current_price is NOT converted - it stays in asset's native currency
        fields_to_convert = [
            "total_cost_basis",
            "total_market_value",
            "total_pnl",
            "avg_cost_per_unit",
        ]

        for field in fields_to_convert:
            if field in position and position[field] is not None:
                converted = CurrencyConversionHelper.convert_value(
                    db,
                    Decimal(str(position[field])),
                    native_currency,
                    display_currency,
                    conversion_date,
                )
                position[field] = float(converted)

        # Convert account-level values
        if "accounts" in position:
            for account in position["accounts"]:
                account_fields = ["cost_basis", "market_value", "pnl"]
                for field in account_fields:
                    if field in account and account[field] is not None:
                        converted = CurrencyConversionHelper.convert_value(
                            db,
                            Decimal(str(account[field])),
                            native_currency,
                            display_currency,
                            conversion_date,
                        )
                        account[field] = float(converted)

        position["display_currency"] = display_currency
        return position

    @staticmethod
    def convert_snapshot_dict(db: Session, snapshot: dict, display_currency: str) -> dict:
        """
        Convert snapshot dictionary to display currency.

        Args:
            db: Database session
            snapshot: Snapshot dict with value_usd and value_ils
            display_currency: Target currency

        Returns:
            Snapshot dict with value in display currency
        """
        # Snapshots store both USD and ILS values
        # Convert from USD to display currency using the snapshot's date
        snapshot_date = date.fromisoformat(snapshot["date"])

        if display_currency == "USD":
            snapshot["value"] = snapshot["value_usd"]
        elif display_currency == "ILS":
            snapshot["value"] = snapshot["value_ils"]
        else:
            # Convert from USD to requested currency
            converted = CurrencyConversionHelper.convert_value(
                db, Decimal(str(snapshot["value_usd"])), "USD", display_currency, snapshot_date
            )
            snapshot["value"] = float(converted)

        snapshot["currency"] = display_currency
        return snapshot
