"""Migrate entity data to portfolio system

Revision ID: migrate_entities_to_portfolios
Revises: add_portfolio_to_account
Create Date: 2026-01-19

This data migration:
1. Creates a user for each entity that has accounts
2. Creates a portfolio for each user (named after entity)
3. Updates accounts to use portfolio_id instead of entity_id
4. Is idempotent - safe to run multiple times
"""

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import text

from alembic import op

revision: str = "migrate_entities_to_portfolios"
down_revision: str | None = "add_portfolio_to_account"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate entities with accounts to the new portfolio system."""
    conn = op.get_bind()

    # Find all entities that have accounts but those accounts don't have portfolio_id
    entities_to_migrate = conn.execute(
        text("""
            SELECT DISTINCT e.id, e.name, e.type
            FROM entities e
            INNER JOIN accounts a ON a.entity_id = e.id
            WHERE a.portfolio_id IS NULL
        """)
    ).fetchall()

    if not entities_to_migrate:
        print("No entities to migrate - all accounts already have portfolio_id")
        return

    for entity_id, entity_name, entity_type in entities_to_migrate:
        # Generate unique IDs
        user_id = str(uuid4())
        portfolio_id = str(uuid4())

        # Create email from entity name (sanitized)
        email_safe_name = entity_name.lower().replace(" ", "_").replace("'", "")
        email = f"{email_safe_name}_{entity_id}@migrated.local"

        # Check if user already exists with this email (idempotent)
        existing_user = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email},
        ).fetchone()

        if existing_user:
            user_id = existing_user[0]
            # Check if portfolio exists for this user
            existing_portfolio = conn.execute(
                text("SELECT id FROM portfolios WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).fetchone()
            if existing_portfolio:
                portfolio_id = existing_portfolio[0]
            else:
                # Create portfolio for existing user
                conn.execute(
                    text("""
                        INSERT INTO portfolios (id, user_id, name, description, created_at, updated_at)
                        VALUES (:id, :user_id, :name, :description, now(), now())
                    """),
                    {
                        "id": portfolio_id,
                        "user_id": user_id,
                        "name": f"{entity_name} Portfolio",
                        "description": f"Migrated from entity: {entity_name} ({entity_type})",
                    },
                )
        else:
            # Create new user (no password - will need to set up auth separately)
            conn.execute(
                text("""
                    INSERT INTO users (id, email, is_active, created_at, updated_at)
                    VALUES (:id, :email, true, now(), now())
                """),
                {"id": user_id, "email": email},
            )

            # Create portfolio for new user
            conn.execute(
                text("""
                    INSERT INTO portfolios (id, user_id, name, description, created_at, updated_at)
                    VALUES (:id, :user_id, :name, :description, now(), now())
                """),
                {
                    "id": portfolio_id,
                    "user_id": user_id,
                    "name": f"{entity_name} Portfolio",
                    "description": f"Migrated from entity: {entity_name} ({entity_type})",
                },
            )

        # Update all accounts for this entity to use the new portfolio_id
        result = conn.execute(
            text("""
                UPDATE accounts
                SET portfolio_id = :portfolio_id
                WHERE entity_id = :entity_id AND portfolio_id IS NULL
            """),
            {"portfolio_id": portfolio_id, "entity_id": entity_id},
        )

        print(
            f"Migrated entity '{entity_name}' (id={entity_id}): "
            f"user_id={user_id}, portfolio_id={portfolio_id}, "
            f"accounts_updated={result.rowcount}"
        )

    print(f"Migration complete: {len(entities_to_migrate)} entities migrated")


def downgrade() -> None:
    """Remove migrated users and portfolios, clear portfolio_id from accounts.

    Note: This only removes data created by this migration (emails ending with @migrated.local)
    """
    conn = op.get_bind()

    # Clear portfolio_id from accounts that were migrated
    # (accounts that have both entity_id and portfolio_id set)
    conn.execute(
        text("""
            UPDATE accounts
            SET portfolio_id = NULL
            WHERE entity_id IS NOT NULL AND portfolio_id IS NOT NULL
        """)
    )

    # Delete portfolios belonging to migrated users
    conn.execute(
        text("""
            DELETE FROM portfolios
            WHERE user_id IN (
                SELECT id FROM users WHERE email LIKE '%@migrated.local'
            )
        """)
    )

    # Delete migrated users
    conn.execute(
        text("DELETE FROM users WHERE email LIKE '%@migrated.local'")
    )

    print("Downgrade complete: Removed migrated users and portfolios")
