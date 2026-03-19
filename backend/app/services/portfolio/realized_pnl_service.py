"""Realized P&L backfill service.

Replays FIFO lots from raw Transaction records to compute realized_pnl_usd
for sell transactions. Works independently of HoldingLot DB records.
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.repositories import HoldingRepository
from app.services.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


def compute_realized_pnl_usd(
    *,
    sell_quantity: Decimal,
    sell_price_per_unit: Decimal,
    sell_fees: Decimal,
    total_cost_basis_sold: Decimal,
    currency_rate_to_usd: Decimal | None,
) -> Decimal:
    """Compute realized P&L in USD for a single sell transaction.

    Used by both the manual sell path (router) and the FIFO backfill service.
    """
    gross_proceeds = sell_quantity * sell_price_per_unit
    net_proceeds = gross_proceeds - sell_fees
    realized_native = net_proceeds - total_cost_basis_sold
    rate = currency_rate_to_usd if currency_rate_to_usd is not None else Decimal("1")
    return realized_native * rate


class RealizedPnlService:
    """Compute and store realized P&L on sell transactions via FIFO replay."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._holding_repo = HoldingRepository(db)
        self._txn_repo = TransactionRepository(db)

    def backfill_for_accounts(self, account_ids: list[int]) -> int:
        """Compute realized_pnl_usd for sell transactions missing it.

        Replays all transactions per holding chronologically, building FIFO
        lots from Buys and computing realized P&L on Sells.

        Returns the number of transactions updated.
        """
        holding_ids = self._holding_repo.find_ids_by_accounts(account_ids)

        updated = 0
        for holding_id in holding_ids:
            updated += self._backfill_holding(holding_id)

        if updated > 0:
            self._db.flush()

        return updated

    def _backfill_holding(self, holding_id: int) -> int:
        """Replay FIFO for a single holding and fill realized_pnl_usd on sells."""
        transactions = self._txn_repo.find_by_holding_ordered(holding_id)

        lots: list[dict] = []
        updated = 0

        for txn in transactions:
            if txn.type == "Buy":
                quantity = txn.quantity or Decimal("0")
                price = txn.price_per_unit or Decimal("0")
                fees = txn.fees or Decimal("0")
                lots.append(
                    {
                        "quantity": quantity,
                        "remaining": quantity,
                        "cost_per_unit": price,
                        "fees": fees,
                    }
                )

            elif txn.type == "Sell":
                if txn.realized_pnl_usd is not None:
                    # Already backfilled — still consume lots to keep FIFO state correct
                    self._consume_lots(lots, abs(txn.quantity or Decimal("0")))
                    continue

                sell_qty = abs(txn.quantity or Decimal("0"))
                cost_basis_sold = self._consume_lots(lots, sell_qty)

                txn.realized_pnl_usd = compute_realized_pnl_usd(
                    sell_quantity=sell_qty,
                    sell_price_per_unit=txn.price_per_unit or Decimal("0"),
                    sell_fees=txn.fees or Decimal("0"),
                    total_cost_basis_sold=cost_basis_sold,
                    currency_rate_to_usd=txn.currency_rate_to_usd_at_date,
                )
                updated += 1

            elif txn.type not in (
                "Deposit",
                "Withdrawal",
                "Dividend",
                "Tax",
                "Fee",
                "Transfer",
                "Custody Fee",
                "Interest",
                "Forex Conversion",
                "Credit",
            ):
                logger.warning(
                    "Unrecognized transaction type %r for holding %d (txn %d) — "
                    "may affect FIFO lot state",
                    txn.type,
                    holding_id,
                    txn.id,
                )

        return updated

    @staticmethod
    def _consume_lots(lots: list[dict], sell_qty: Decimal) -> Decimal:
        """Walk FIFO lots and return total cost basis sold.

        Matches PortfolioReconstructionService logic (lines 149-173):
        includes proportional buy fees in cost basis.
        """
        remaining = sell_qty
        cost_basis_sold = Decimal("0")

        for lot in lots:
            if remaining <= 0:
                break

            available = lot["remaining"]
            if available <= 0:
                continue

            sold = min(available, remaining)
            lot["remaining"] -= sold

            cost_per_unit = lot.get("cost_per_unit") or Decimal("0")
            cost = sold * cost_per_unit

            lot_qty = lot.get("quantity") or Decimal("0")
            lot_fees = lot.get("fees") or Decimal("0")
            if lot_qty > 0:
                fee_proportion = (sold / lot_qty) * lot_fees
                cost += fee_proportion

            cost_basis_sold += cost
            remaining -= sold

        return cost_basis_sold
