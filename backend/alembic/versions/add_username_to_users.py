"""add_username_to_users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10

"""

import re
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _generate_username(email: str) -> str:
    """Extract username from email prefix, sanitize to [a-z0-9_]."""
    prefix = email.split("@")[0].lower()
    sanitized = re.sub(r"[^a-z0-9_]", "_", prefix)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:27] if sanitized else "user"


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(30), nullable=True))

    # Backfill existing users from email prefix
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id, email FROM users")).fetchall()
    taken: set[str] = set()
    for user_id, email in users:
        base = _generate_username(email)
        candidate = base
        counter = 1
        while candidate in taken:
            suffix = str(counter)
            candidate = base[: 30 - len(suffix)] + suffix
            counter += 1
        taken.add(candidate)
        conn.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": candidate, "id": user_id},
        )

    op.alter_column("users", "username", nullable=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
