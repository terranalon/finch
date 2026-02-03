"""User data access layer."""

import logging

from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Centralized user data access.

    Naming conventions:
    - find_* : Query that may return None
    - get_* : Query that raises exception if missing
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, user_id: str) -> User | None:
        """Find user by primary key."""
        return self._db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> User | None:
        """Find user by email (case-insensitive)."""
        return self._db.query(User).filter(User.email.ilike(email)).first()

    def find_active_by_id(self, user_id: str) -> User | None:
        """Find active user by ID."""
        return self._db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()

    def find_verified_by_email(self, email: str) -> User | None:
        """Find verified, active user by email."""
        return (
            self._db.query(User)
            .filter(
                User.email.ilike(email),
                User.is_active.is_(True),
                User.email_verified.is_(True),
            )
            .first()
        )
