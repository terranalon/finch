"""Consolidate legacy forex pairs into single-row format

Revision ID: consolidate_legacy_forex_pairs
Revises: rename_sector_to_category
Create Date: 2026-02-15

Legacy IBKR forex imports created TWO transaction rows per conversion.
This migration consolidates each pair into a single row:
1. Enriches the "from" row with to_holding_id, to_amount, exchange_rate
2. Normalizes amount to positive (matching new-format convention)
3. Deletes the mirror "to" row
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import text

from alembic import op

revision: str = "consolidate_legacy_forex_pairs"
down_revision: str | None = "rename_sector_to_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOTES_RE = re.compile(r"Convert ([\d.]+) (\w+) to ([\d.]+) (\w+) @ ([\d.]+)")


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        text("""
            SELECT t.id, t.date, t.notes, t.holding_id, a.symbol, h.account_id
            FROM transactions t
            JOIN holdings h ON t.holding_id = h.id
            JOIN assets a ON h.asset_id = a.id
            WHERE t.type = 'Forex Conversion'
              AND t.to_holding_id IS NULL
              AND t.notes IS NOT NULL
            ORDER BY t.date, t.id
        """)
    ).fetchall()

    if not rows:
        print("No legacy forex pairs to migrate")
        return

    groups: dict[tuple, list] = defaultdict(list)
    for txn_id, txn_date, notes, holding_id, symbol, account_id in rows:
        match = _NOTES_RE.search(notes)
        if not match:
            continue
        key = (str(txn_date), notes)
        groups[key].append(
            {
                "id": txn_id,
                "holding_id": holding_id,
                "symbol": symbol,
                "account_id": account_id,
                "from_amt": Decimal(match.group(1)),
                "from_curr": match.group(2),
                "to_amt": Decimal(match.group(3)),
                "to_curr": match.group(4),
                "rate": Decimal(match.group(5)),
            }
        )

    migrated = 0
    deleted = 0
    skipped = 0

    for _key, group in groups.items():
        parsed = group[0]
        from_curr = parsed["from_curr"]
        to_curr = parsed["to_curr"]
        from_amt = parsed["from_amt"]
        to_amt = parsed["to_amt"]
        rate = parsed["rate"]

        from_row = next((r for r in group if r["symbol"] == from_curr), None)
        to_row = next((r for r in group if r["symbol"] == to_curr), None)

        if from_row is None:
            from_row = group[0]

        if to_row is not None:
            to_holding_id = to_row["holding_id"]
        else:
            result = conn.execute(
                text("""
                    SELECT h.id FROM holdings h
                    JOIN assets a ON h.asset_id = a.id
                    WHERE h.account_id = :account_id AND a.symbol = :symbol
                    LIMIT 1
                """),
                {"account_id": from_row["account_id"], "symbol": to_curr},
            ).fetchone()
            if result is None:
                skipped += 1
                continue
            to_holding_id = result[0]

        conn.execute(
            text("""
                UPDATE transactions
                SET to_holding_id = :to_holding_id,
                    to_amount = :to_amount,
                    exchange_rate = :exchange_rate,
                    amount = :amount
                WHERE id = :id
            """),
            {
                "id": from_row["id"],
                "to_holding_id": to_holding_id,
                "to_amount": float(to_amt),
                "exchange_rate": float(rate),
                "amount": float(from_amt),
            },
        )
        migrated += 1

        if to_row is not None and to_row["id"] != from_row["id"]:
            conn.execute(
                text("DELETE FROM transactions WHERE id = :id"),
                {"id": to_row["id"]},
            )
            deleted += 1

    print(
        f"Forex migration: {migrated} pairs converted, "
        f"{deleted} mirror rows deleted, {skipped} skipped"
    )


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        text("""
            UPDATE transactions
            SET to_holding_id = NULL, to_amount = NULL, exchange_rate = NULL
            WHERE type = 'Forex Conversion'
              AND to_holding_id IS NOT NULL
              AND notes LIKE '%Convert % to % @ %'
        """)
    )
    print(f"Forex downgrade: {result.rowcount} rows reverted (mirrors NOT restored)")
