"""Tests for common response schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
)


class ItemSchema(BaseModel):
    """Test item schema for pagination tests."""

    id: int
    name: str


class TestPaginatedResponse:
    """Tests for PaginatedResponse generic schema."""

    def test_paginated_response_structure(self):
        """Test basic structure with required fields."""
        items = [ItemSchema(id=1, name="test")]
        response = PaginatedResponse[ItemSchema](
            items=items,
            total=100,
            skip=0,
            limit=10,
            has_more=True,
        )
        assert response.items == items
        assert response.total == 100
        assert response.skip == 0
        assert response.limit == 10
        assert response.has_more is True

    def test_paginated_response_serialization(self):
        """Test serialization to dict."""
        response = PaginatedResponse[ItemSchema](
            items=[ItemSchema(id=1, name="test")],
            total=1,
            skip=0,
            limit=10,
            has_more=False,
        )
        data = response.model_dump()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data

    def test_paginated_response_empty_items(self):
        """Test with empty items list."""
        response = PaginatedResponse[ItemSchema](
            items=[],
            total=0,
            skip=0,
            limit=10,
            has_more=False,
        )
        assert response.items == []
        assert response.total == 0
        assert response.has_more is False

    def test_paginated_response_has_more_true(self):
        """Test has_more is True when more items exist."""
        response = PaginatedResponse[ItemSchema](
            items=[ItemSchema(id=1, name="first")],
            total=100,
            skip=0,
            limit=1,
            has_more=True,
        )
        assert response.has_more is True

    def test_paginated_response_has_more_false_at_end(self):
        """Test has_more is False at end of list."""
        response = PaginatedResponse[ItemSchema](
            items=[ItemSchema(id=10, name="last")],
            total=10,
            skip=9,
            limit=10,
            has_more=False,
        )
        assert response.has_more is False

    def test_paginated_response_missing_required_field(self):
        """Test validation error when required field is missing."""
        with pytest.raises(ValidationError):
            PaginatedResponse[ItemSchema](
                items=[],
                # missing: total, skip, limit, has_more
            )


class TestErrorDetail:
    """Tests for ErrorDetail schema."""

    def test_error_detail_with_field(self):
        """Test error detail with field specified."""
        detail = ErrorDetail(field="email", message="Invalid email format")
        assert detail.field == "email"
        assert detail.message == "Invalid email format"

    def test_error_detail_without_field(self):
        """Test error detail without field (general error)."""
        detail = ErrorDetail(message="Something went wrong")
        assert detail.field is None
        assert detail.message == "Something went wrong"

    def test_error_detail_serialization(self):
        """Test serialization to dict."""
        detail = ErrorDetail(field="password", message="Too short")
        data = detail.model_dump()
        assert data["field"] == "password"
        assert data["message"] == "Too short"


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_error_response_structure(self):
        """Test basic error response structure."""
        error = ErrorResponse(
            error="NotFound",
            message="User not found",
            path="/api/users/123",
        )
        assert error.error == "NotFound"
        assert error.message == "User not found"
        assert error.path == "/api/users/123"
        assert isinstance(error.timestamp, datetime)

    def test_error_response_with_details(self):
        """Test error response with multiple error details."""
        details = [
            ErrorDetail(field="email", message="Required"),
            ErrorDetail(field="password", message="Too short"),
        ]
        error = ErrorResponse(
            error="ValidationError",
            message="Validation failed",
            details=details,
        )
        assert error.details is not None
        assert len(error.details) == 2
        assert error.details[0].field == "email"
        assert error.details[1].field == "password"

    def test_error_response_without_details(self):
        """Test error response without details."""
        error = ErrorResponse(
            error="InternalError",
            message="An unexpected error occurred",
        )
        assert error.details is None

    def test_error_response_timestamp_auto_generated(self):
        """Test that timestamp is automatically generated."""
        before = datetime.now(UTC)
        error = ErrorResponse(
            error="Test",
            message="Test error",
        )
        after = datetime.now(UTC)

        assert error.timestamp >= before
        assert error.timestamp <= after

    def test_error_response_serialization(self):
        """Test serialization to dict includes all fields."""
        error = ErrorResponse(
            error="NotFound",
            message="Resource not found",
            path="/api/resource/1",
        )
        data = error.model_dump()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        assert "path" in data
        assert "details" in data


class TestMessageResponse:
    """Tests for MessageResponse schema."""

    def test_message_response_structure(self):
        """Test basic message response."""
        response = MessageResponse(message="Operation successful")
        assert response.message == "Operation successful"

    def test_message_response_serialization(self):
        """Test serialization to dict."""
        response = MessageResponse(message="Done")
        data = response.model_dump()
        assert data["message"] == "Done"

    def test_message_response_missing_message(self):
        """Test validation error when message is missing."""
        with pytest.raises(ValidationError):
            MessageResponse()
