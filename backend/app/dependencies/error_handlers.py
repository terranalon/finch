"""Global exception handlers that produce ErrorResponse JSON.

Registered in app/main.py. Three handlers:
- app_error_handler: catches domain AppError exceptions
- http_exception_handler: safety net for FastAPI's HTTPException
- validation_exception_handler: converts Pydantic validation errors
"""

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import AppError
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

_STATUS_TO_ERROR_CODE: dict[int, str] = {
    400: "BadRequest",
    401: "Unauthorized",
    403: "Forbidden",
    404: "NotFound",
    409: "Conflict",
    422: "ValidationError",
    429: "RateLimited",
    500: "InternalError",
}


def _build_response(
    status_code: int,
    error_response: ErrorResponse,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json"),
        headers=headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle domain exceptions (AppError subclasses)."""
    if exc.private_message:
        logger.error(
            "%s: %s (private: %s) path=%s",
            exc.error_code,
            exc.message,
            exc.private_message,
            request.url.path,
        )

    return _build_response(
        exc.status_code,
        ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            extra=exc.extra,
            path=request.url.path,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Safety net for HTTPException from FastAPI internals or unmigrated code."""
    headers: dict[str, str] | None = getattr(exc, "headers", None)

    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        extra_data: dict[str, Any] = {
            k: v for k, v in exc.detail.items() if k not in ("message", "error", "error_code")
        }
        extra = extra_data if extra_data else None
    else:
        message = str(exc.detail) if exc.detail else "An error occurred"
        extra = None

    error_code = _STATUS_TO_ERROR_CODE.get(exc.status_code, "Error")

    return _build_response(
        exc.status_code,
        ErrorResponse(
            error=error_code,
            message=message,
            extra=extra,
            path=request.url.path,
        ),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors to ErrorResponse with field-level details."""
    details: list[ErrorDetail] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        # Strip leading "body" prefix for cleaner field paths
        if loc and loc[0] == "body":
            loc = loc[1:]
        field = ".".join(str(part) for part in loc) if loc else None
        details = [*details, ErrorDetail(field=field, message=err["msg"])]

    return _build_response(
        422,
        ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details=details,
            path=request.url.path,
        ),
    )
