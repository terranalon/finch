"""Domain exception hierarchy for structured API error responses.

All exceptions inherit from AppError and carry:
- status_code: HTTP status code
- error_code: Machine-readable string (e.g., "NotFound")
- message: Human-readable message (safe for API consumers)
- extra: Optional structured data for domain-specific context
- private_message: Optional internal detail for server logs (never exposed)
"""

from typing import Any


class AppError(Exception):
    """Base application error. Maps to ErrorResponse JSON."""

    status_code: int = 500
    error_code: str = "InternalError"

    def __init__(
        self,
        message: str,
        *,
        extra: dict[str, Any] | None = None,
        private_message: str | None = None,
    ) -> None:
        self.message = message
        self.extra = extra
        self.private_message = private_message
        super().__init__(message)


class BadRequestError(AppError):
    status_code = 400
    error_code = "BadRequest"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "Forbidden"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NotFound"

    def __init__(
        self,
        resource: str,
        identifier: str | int,
        *,
        private_message: str | None = None,
    ) -> None:
        super().__init__(
            f"{resource} with id {identifier} not found",
            extra={"resource": resource, "identifier": identifier},
            private_message=private_message,
        )


class ConflictError(AppError):
    status_code = 409
    error_code = "Conflict"


class UnprocessableEntityError(AppError):
    status_code = 422
    error_code = "UnprocessableEntity"
