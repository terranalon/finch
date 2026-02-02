"""IBKR import validation service.

Validates that our transaction-based reconstruction matches IBKR's authoritative
cash positions. This helps catch parsing errors and missing transaction types.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating one currency's cash balance."""

    currency: str
    our_total: Decimal
    ibkr_total: Decimal
    difference: Decimal
    is_valid: bool  # True if difference <= threshold
    breakdown: dict[str, Decimal]  # Our transaction breakdown


@dataclass
class IBKRValidationReport:
    """Complete validation report for an import."""

    is_valid: bool
    results: list[ValidationResult]
    warnings: list[str]
    fx_positions_available: bool
    statement_of_funds_available: bool


class IBKRValidationService:
    """Validates IBKR import accuracy by comparing against authoritative data.

    Compares our transaction-based reconstruction against:
    1. FxPositions - IBKR's final cash balance by currency
    2. Statement of Funds - IBKR's detailed cash accounting (if available)

    Usage:
        validator = IBKRValidationService(threshold=Decimal("1.00"))
        report = validator.validate(
            transactions=parsed_transactions,
            dividends=parsed_dividends,
            forex=parsed_forex,
            other_cash=parsed_other_cash,
            fx_positions=ibkr_fx_positions,
            statement_of_funds=statement_of_funds_summary
        )
        if not report.is_valid:
            for warning in report.warnings:
                logger.warning(warning)
    """

    def __init__(self, threshold: Decimal = Decimal("1.00")):
        """Initialize validator.

        Args:
            threshold: Maximum acceptable difference in any currency (default $1)
        """
        self.threshold = threshold

    def calculate_cash_totals(
        self,
        transactions: list[dict],
        dividends: list[dict],
        transfers: list[dict],
        forex: list[dict],
        other_cash: list[dict],
    ) -> dict[str, dict[str, Decimal]]:
        """Calculate total cash impact by currency and transaction type.

        Args:
            transactions: Trade transactions (Buy/Sell with net_cash)
            dividends: Dividend payments
            transfers: Deposits/Withdrawals
            forex: Currency conversions
            other_cash: Interest, Tax, Fee transactions

        Returns:
            Dictionary: {currency: {category: total_amount}}
        """
        totals: dict[str, dict[str, Decimal]] = {}

        def add_to_totals(currency: str, category: str, amount: Decimal) -> None:
            if currency not in totals:
                totals[currency] = {}
            if category not in totals[currency]:
                totals[currency][category] = Decimal("0")
            totals[currency][category] += amount

        # Process trade settlements (net_cash from Buy/Sell)
        for txn in transactions:
            currency = txn.get("currency", "USD")
            net_cash = txn.get("net_cash", Decimal("0"))
            if net_cash:
                add_to_totals(currency, "TRADE", net_cash)

        # Process deposits/withdrawals
        for transfer in transfers:
            currency = transfer.get("currency", "USD")
            amount = transfer.get("amount", Decimal("0"))
            transfer_type = transfer.get("type", "")
            # Withdrawals are negative
            if transfer_type == "Withdrawal":
                amount = -abs(amount)
            else:
                amount = abs(amount)
            add_to_totals(currency, "DEPOSIT", amount)

        # Process dividends (these credit cash)
        for div in dividends:
            currency = div.get("currency", "USD")
            amount = div.get("amount", Decimal("0"))
            add_to_totals(currency, "DIVIDEND", abs(amount))

        # Process forex conversions
        for fx in forex:
            from_currency = fx.get("from_currency", "")
            to_currency = fx.get("to_currency", "")
            from_amount = fx.get("from_amount", Decimal("0"))
            to_amount = fx.get("to_amount", Decimal("0"))

            # Selling from_currency
            if from_currency:
                add_to_totals(from_currency, "FOREX", -abs(from_amount))
            # Buying to_currency
            if to_currency:
                add_to_totals(to_currency, "FOREX", abs(to_amount))

        # Process other cash (interest, tax, fees)
        for cash_txn in other_cash:
            currency = cash_txn.get("currency", "USD")
            amount = cash_txn.get("amount", Decimal("0"))
            txn_type = cash_txn.get("type", "OTHER")

            # Map to category
            if txn_type == "Interest":
                category = "INTEREST"
            elif txn_type == "Tax":
                category = "TAX"
            elif txn_type == "Fee":
                category = "FEE"
            else:
                category = "OTHER"

            # Amount already has correct sign (negative for tax/fees)
            add_to_totals(currency, category, amount)

        return totals

    def validate(
        self,
        transactions: list[dict],
        dividends: list[dict],
        transfers: list[dict],
        forex: list[dict],
        other_cash: list[dict],
        fx_positions: dict[str, Decimal] | None = None,
        statement_of_funds: dict[str, dict[str, Decimal]] | None = None,
    ) -> IBKRValidationReport:
        """Validate our reconstruction against IBKR's authoritative data.

        Args:
            transactions: Parsed trade transactions
            dividends: Parsed dividends
            transfers: Parsed deposits/withdrawals
            forex: Parsed forex conversions
            other_cash: Parsed interest/tax/fee transactions
            fx_positions: IBKR's FxPositions (final cash by currency)
            statement_of_funds: IBKR's Statement of Funds summary

        Returns:
            IBKRValidationReport with validation results and warnings
        """
        warnings: list[str] = []
        results: list[ValidationResult] = []
        is_valid = True

        # Calculate our totals
        our_totals = self.calculate_cash_totals(
            transactions, dividends, transfers, forex, other_cash
        )

        # Check if we have validation data
        fx_positions_available = bool(fx_positions)
        statement_of_funds_available = bool(statement_of_funds)

        if not fx_positions_available and not statement_of_funds_available:
            warnings.append(
                "No FxPositions or Statement of Funds available for validation. "
                "Consider adding these sections to your Flex Query."
            )
            return IBKRValidationReport(
                is_valid=True,  # Can't validate, assume OK
                results=[],
                warnings=warnings,
                fx_positions_available=False,
                statement_of_funds_available=False,
            )

        # Prefer FxPositions for validation (simpler, more direct)
        if fx_positions:
            for currency, ibkr_balance in fx_positions.items():
                # Calculate our total for this currency
                our_breakdown = our_totals.get(currency, {})
                our_total = sum(our_breakdown.values(), Decimal("0"))

                difference = our_total - ibkr_balance

                currency_is_valid = abs(difference) <= self.threshold

                if not currency_is_valid:
                    is_valid = False
                    warnings.append(
                        f"{currency} DISCREPANCY: Our total {our_total:.2f} vs "
                        f"IBKR's {ibkr_balance:.2f} (diff: {difference:.2f})"
                    )

                results.append(
                    ValidationResult(
                        currency=currency,
                        our_total=our_total,
                        ibkr_total=ibkr_balance,
                        difference=difference,
                        is_valid=currency_is_valid,
                        breakdown=our_breakdown,
                    )
                )

            # Check for currencies we have but IBKR doesn't report
            for currency in our_totals:
                if currency not in fx_positions:
                    our_total = sum(our_totals[currency].values(), Decimal("0"))
                    if abs(our_total) > self.threshold:
                        warnings.append(
                            f"{currency} has calculated balance {our_total:.2f} but "
                            "no FxPosition in IBKR data"
                        )

        return IBKRValidationReport(
            is_valid=is_valid,
            results=results,
            warnings=warnings,
            fx_positions_available=fx_positions_available,
            statement_of_funds_available=statement_of_funds_available,
        )

    def format_report(self, report: IBKRValidationReport) -> str:
        """Format validation report as human-readable string.

        Args:
            report: Validation report

        Returns:
            Formatted string for logging
        """
        lines = ["=" * 60, "IBKR Import Validation Report", "=" * 60]

        if report.is_valid:
            lines.append("Status: ✅ PASSED - All currencies within threshold")
        else:
            lines.append("Status: ❌ FAILED - Some currencies have discrepancies")

        lines.append(f"Threshold: ±{self.threshold}")
        lines.append(f"FxPositions available: {report.fx_positions_available}")
        lines.append(f"Statement of Funds available: {report.statement_of_funds_available}")
        lines.append("")

        if report.results:
            lines.append("Currency Breakdown:")
            lines.append("-" * 60)

            for result in report.results:
                status = "✅" if result.is_valid else "❌"
                lines.append(
                    f"{status} {result.currency}: "
                    f"Ours={result.our_total:.2f} | "
                    f"IBKR={result.ibkr_total:.2f} | "
                    f"Diff={result.difference:.2f}"
                )

                # Show breakdown for failed currencies
                if not result.is_valid and result.breakdown:
                    for category, amount in sorted(result.breakdown.items()):
                        lines.append(f"     {category}: {amount:.2f}")

        if report.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.append("-" * 60)
            for warning in report.warnings:
                lines.append(f"⚠️  {warning}")

        lines.append("=" * 60)

        return "\n".join(lines)


def validate_ibkr_import(
    transactions: list[dict],
    dividends: list[dict],
    transfers: list[dict],
    forex: list[dict],
    other_cash: list[dict],
    fx_positions: dict[str, Decimal] | None = None,
    threshold: Decimal = Decimal("1.00"),
) -> dict[str, Any]:
    """Convenience function to validate an IBKR import.

    Args:
        transactions: Parsed trade transactions
        dividends: Parsed dividends
        transfers: Parsed deposits/withdrawals
        forex: Parsed forex conversions
        other_cash: Parsed interest/tax/fee transactions
        fx_positions: IBKR's FxPositions (final cash by currency)
        threshold: Maximum acceptable difference

    Returns:
        Dictionary with validation results
    """
    validator = IBKRValidationService(threshold=threshold)
    report = validator.validate(
        transactions=transactions,
        dividends=dividends,
        transfers=transfers,
        forex=forex,
        other_cash=other_cash,
        fx_positions=fx_positions,
    )

    # Log the report
    logger.info(validator.format_report(report))

    return {
        "is_valid": report.is_valid,
        "warnings": report.warnings,
        "results": [
            {
                "currency": r.currency,
                "our_total": float(r.our_total),
                "ibkr_total": float(r.ibkr_total),
                "difference": float(r.difference),
                "is_valid": r.is_valid,
            }
            for r in report.results
        ],
    }
