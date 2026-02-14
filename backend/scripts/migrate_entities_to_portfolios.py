"""Migrate Entity→Account to User→Portfolio→Account hierarchy."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

MIGRATION_USER_EMAIL = "migrated@finch.local"
MIGRATION_USER_PASSWORD = "migrated-user-change-me"


def migrate_entities(db: DBSession) -> dict:
    """
    Migrate existing Entity→Account data to User→Portfolio→Account.

    Strategy:
    1. Create a default "migration user" for existing data
    2. For each Entity, create a Portfolio with same name
    3. Link all entity's accounts to the new portfolio

    Returns:
        Dict with migration statistics
    """
    stats = {
        "user_created": False,
        "portfolios_created": 0,
        "accounts_updated": 0,
    }

    # Step 1: Create or get migration user
    user = db.query(User).filter(User.email == MIGRATION_USER_EMAIL).first()
    if not user:
        user = User(
            email=MIGRATION_USER_EMAIL,
            password_hash=AuthService.hash_password(MIGRATION_USER_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.flush()
        stats["user_created"] = True
        logger.info(f"Created migration user: {user.email}")

    # Step 2: Get all entities
    entities_result = db.execute(text("SELECT id, name, type FROM entities"))
    entities = entities_result.fetchall()

    # Track entity_id -> portfolio_id mapping
    entity_to_portfolio = {}

    for entity_id, entity_name, entity_type in entities:
        # Check if portfolio already exists for this entity
        # (using description to track source entity_id)
        existing = (
            db.query(Portfolio)
            .filter(
                Portfolio.user_id == user.id,
                Portfolio.description.like(f"%entity_id:{entity_id}%"),
            )
            .first()
        )

        if existing:
            entity_to_portfolio[entity_id] = existing.id
            logger.debug(f"Portfolio already exists for entity {entity_id}")
            continue

        # Create new portfolio
        portfolio = Portfolio(
            user_id=user.id,
            name=entity_name,
            description=f"Migrated from {entity_type}. Original entity_id:{entity_id}",
        )
        db.add(portfolio)
        db.flush()
        entity_to_portfolio[entity_id] = portfolio.id
        stats["portfolios_created"] += 1
        logger.info(f"Created portfolio '{entity_name}' for entity {entity_id}")

    # Step 3: Update accounts to link to portfolios
    for entity_id, portfolio_id in entity_to_portfolio.items():
        result = db.execute(
            text(
                "UPDATE accounts SET portfolio_id = :portfolio_id "
                "WHERE entity_id = :entity_id AND portfolio_id IS NULL"
            ),
            {"portfolio_id": portfolio_id, "entity_id": entity_id},
        )
        stats["accounts_updated"] += result.rowcount

    db.commit()
    logger.info(f"Migration complete: {stats}")
    return stats


if __name__ == "__main__":
    """Run as standalone script."""
    logging.basicConfig(level=logging.INFO)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        stats = migrate_entities(db)
        print(f"Migration complete: {stats}")
    finally:
        db.close()
