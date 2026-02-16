"""Tests for global exception handlers."""

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.dependencies.error_handlers import (
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.exceptions import BadRequestError, ConflictError, NotFoundError


def _make_request(path: str = "/api/test") -> MagicMock:
    """Create a mock Request with url.path."""
    request = MagicMock()
    request.url.path = path
    return request


def _parse_response(response) -> dict:
    """Parse JSONResponse content."""
    return json.loads(response.body.decode())


@pytest.mark.asyncio
class TestAppErrorHandler:
    async def test_not_found_error(self):
        request = _make_request("/api/accounts/42")
        exc = NotFoundError("Account", 42)
        response = await app_error_handler(request, exc)

        assert response.status_code == 404
        body = _parse_response(response)
        assert body["error"] == "NotFound"
        assert "Account" in body["message"]
        assert body["path"] == "/api/accounts/42"
        assert "timestamp" in body
        assert body["extra"]["resource"] == "Account"

    async def test_conflict_with_extra(self):
        request = _make_request()
        exc = ConflictError("Overlap", extra={"hint": "Use confirm_overlap=true"})
        response = await app_error_handler(request, exc)

        assert response.status_code == 409
        body = _parse_response(response)
        assert body["extra"]["hint"] == "Use confirm_overlap=true"

    async def test_private_message_not_exposed(self):
        request = _make_request()
        exc = BadRequestError("Bad input", private_message="SQL column xyz")
        response = await app_error_handler(request, exc)

        body = _parse_response(response)
        assert "SQL column xyz" not in json.dumps(body)

    async def test_details_is_none_for_non_validation(self):
        request = _make_request()
        exc = NotFoundError("Account", 1)
        response = await app_error_handler(request, exc)

        body = _parse_response(response)
        assert body["details"] is None


@pytest.mark.asyncio
class TestHTTPExceptionHandler:
    async def test_standard_404(self):
        request = _make_request("/api/things/1")
        exc = HTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(request, exc)

        assert response.status_code == 404
        body = _parse_response(response)
        assert body["error"] == "NotFound"
        assert body["message"] == "Not found"
        assert body["path"] == "/api/things/1"

    async def test_401_with_headers(self):
        request = _make_request()
        exc = HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        response = await http_exception_handler(request, exc)

        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Bearer"

    async def test_dict_detail_extracts_message(self):
        request = _make_request()
        exc = HTTPException(
            status_code=409,
            detail={
                "error": "Date range overlap",
                "message": "Overlaps with source X",
                "conflicting_source": {"id": 5},
            },
        )
        response = await http_exception_handler(request, exc)

        body = _parse_response(response)
        assert body["message"] == "Overlaps with source X"
        assert body["extra"]["conflicting_source"]["id"] == 5

    async def test_unknown_status_code_defaults(self):
        request = _make_request()
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        response = await http_exception_handler(request, exc)

        body = _parse_response(response)
        assert body["error"] == "Error"


@pytest.mark.asyncio
class TestValidationExceptionHandler:
    async def test_flattens_loc_path(self):
        request = _make_request("/api/accounts")
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "user", "email"),
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        )
        response = await validation_exception_handler(request, exc)

        assert response.status_code == 422
        body = _parse_response(response)
        assert body["error"] == "ValidationError"
        assert body["details"][0]["field"] == "user.email"
        assert body["details"][0]["message"] == "field required"

    async def test_strips_body_prefix_from_loc(self):
        request = _make_request()
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "name"),
                    "msg": "String should have at least 1 character",
                    "type": "string_too_short",
                }
            ]
        )
        response = await validation_exception_handler(request, exc)

        body = _parse_response(response)
        assert body["details"][0]["field"] == "name"

    async def test_query_param_validation(self):
        request = _make_request()
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("query", "limit"),
                    "msg": "Input should be a valid integer",
                    "type": "int_parsing",
                }
            ]
        )
        response = await validation_exception_handler(request, exc)

        body = _parse_response(response)
        assert body["details"][0]["field"] == "query.limit"
