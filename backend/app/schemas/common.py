"""Common response schemas used across the API."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper.

    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        skip: Number of items skipped (offset)
        limit: Maximum items per page
        has_more: Whether more items exist beyond the current page
    """

    items: list[T]
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether more items exist")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        skip: int,
        limit: int,
    ) -> "PaginatedResponse[T]":
        """Build a paginated response, computing has_more automatically."""
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items)) < total,
        )


class ErrorDetail(BaseModel):
    """Detailed error information for a specific field or issue.

    Attributes:
        field: The field name that caused the error (None for general errors)
        message: Human-readable error description
    """

    field: str | None = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Standard error response format for API errors.

    Attributes:
        error: Error code (e.g., 'NotFound', 'ValidationError')
        message: Human-readable error message
        details: Additional error details (e.g., validation errors per field)
        timestamp: When the error occurred
        path: Request path that caused the error
    """

    error: str = Field(..., description="Error code (e.g., 'NotFound', 'ValidationError')")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(None, description="Additional error details")
    extra: dict[str, Any] | None = Field(None, description="Structured error-specific data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    path: str | None = Field(None, description="Request path that caused the error")


error_responses: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


class MessageResponse(BaseModel):
    """Simple message response for operations that return only a message.

    Attributes:
        message: The response message
    """

    message: str


class StatusResponse(BaseModel):
    """Base for responses that carry a status and message."""

    status: str
    message: str
