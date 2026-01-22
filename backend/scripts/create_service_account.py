"""Create service account for Airflow automated imports."""

import logging
import os
import secrets

from sqlalchemy.orm import Session as DBSession

from app.models.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

SERVICE_EMAIL = "airflow-service@system.internal"


def generate_secure_password() -> str:
    """Generate a cryptographically secure password."""
    return secrets.token_urlsafe(32)


def create_service_account(db: DBSession, password: str | None = None) -> tuple[User, str]:
    """
    Create or retrieve the Airflow service account.

    Args:
        db: Database session
        password: Optional password. If not provided, generates a secure one.

    Returns:
        Tuple of (User, password_used)
    """
    existing_user = db.query(User).filter(User.email == SERVICE_EMAIL).first()

    if existing_user:
        logger.info("Service account already exists: %s", existing_user.id)
        if password:
            existing_user.password_hash = AuthService.hash_password(password)
            db.commit()
            logger.info("Password updated for existing service account")
            return existing_user, password
        return existing_user, "(existing - password not changed)"

    # Generate password if not provided
    password = password or os.getenv("AIRFLOW_SERVICE_PASSWORD") or generate_secure_password()

    user = User(
        email=SERVICE_EMAIL,
        password_hash=AuthService.hash_password(password),
        is_active=True,
        is_service_account=True,
    )
    db.add(user)
    db.commit()

    logger.info("Created service account: %s (id: %s)", SERVICE_EMAIL, user.id)
    return user, password


if __name__ == "__main__":
    """Run as standalone script."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        password = sys.argv[1] if len(sys.argv) > 1 else os.getenv("AIRFLOW_SERVICE_PASSWORD")
        user, password_used = create_service_account(db, password)

        logger.info("")
        logger.info("Service account setup complete:")
        logger.info("  Email: %s", user.email)
        logger.info("  ID: %s", user.id)
        logger.info("  Is Service Account: %s", user.is_service_account)

        if password_used != "(existing - password not changed)":
            logger.info("")
            logger.info("  Password: %s", password_used)
            logger.info("")
            logger.info("  IMPORTANT: Save this password securely!")
            logger.info("  Add to airflow/.env:")
            logger.info("    AIRFLOW_SERVICE_EMAIL=%s", SERVICE_EMAIL)
            logger.info("    AIRFLOW_SERVICE_PASSWORD=%s", password_used)
    finally:
        db.close()
