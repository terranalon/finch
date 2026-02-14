"""Corporate action data access layer."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from app.models import CorporateAction


class CorporateActionRepository:
    """Centralized corporate action data access.

    Naming conventions:
    - find_* : Query that may return None or empty collection
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_effective_before(self, as_of_date: date) -> Sequence[CorporateAction]:
        """Find all corporate actions effective on or before a date."""
        return (
            self._db.query(CorporateAction)
            .filter(CorporateAction.effective_date <= as_of_date)
            .all()
        )

    def find_effective_before_ordered(self, end_date: date) -> Sequence[CorporateAction]:
        """Find corporate actions on or before end_date, ordered by effective_date."""
        return (
            self._db.query(CorporateAction)
            .filter(CorporateAction.effective_date <= end_date)
            .order_by(CorporateAction.effective_date)
            .all()
        )
