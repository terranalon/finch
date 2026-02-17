"""Admin authentication dependency."""

from fastapi import Depends

from app.dependencies.auth import get_current_user
from app.exceptions import ForbiddenError
from app.models.user import User


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges.

    Args:
        current_user: The authenticated user from get_current_user dependency.

    Returns:
        The user if they are an admin.

    Raises:
        ForbiddenError: If the user is not an admin.
    """
    if not current_user.is_admin:
        raise ForbiddenError("Admin access required")
    return current_user
