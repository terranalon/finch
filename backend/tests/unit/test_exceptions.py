"""Tests for domain exception hierarchy."""

from app.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class TestAppError:
    def test_base_error_has_defaults(self):
        err = AppError("Something went wrong")
        assert err.status_code == 500
        assert err.error_code == "InternalError"
        assert err.message == "Something went wrong"
        assert err.extra is None
        assert err.private_message is None

    def test_base_error_with_extra(self):
        err = AppError("fail", extra={"key": "val"})
        assert err.extra == {"key": "val"}

    def test_base_error_with_private_message(self):
        err = AppError("Public msg", private_message="DB column xyz failed")
        assert err.message == "Public msg"
        assert err.private_message == "DB column xyz failed"


class TestNotFoundError:
    def test_defaults(self):
        err = NotFoundError("Account", 42)
        assert err.status_code == 404
        assert err.error_code == "NotFound"
        assert "Account" in err.message
        assert "42" in err.message

    def test_extra_populated(self):
        err = NotFoundError("Account", 42)
        assert err.extra == {"resource": "Account", "identifier": 42}


class TestBadRequestError:
    def test_defaults(self):
        err = BadRequestError("Invalid date range")
        assert err.status_code == 400
        assert err.error_code == "BadRequest"


class TestUnauthorizedError:
    def test_defaults(self):
        err = UnauthorizedError("Invalid credentials")
        assert err.status_code == 401
        assert err.error_code == "Unauthorized"


class TestForbiddenError:
    def test_defaults(self):
        err = ForbiddenError("Admin access required")
        assert err.status_code == 403
        assert err.error_code == "Forbidden"


class TestConflictError:
    def test_defaults(self):
        err = ConflictError("Account 'Kraken' already exists")
        assert err.status_code == 409
        assert err.error_code == "Conflict"

    def test_with_extra(self):
        err = ConflictError(
            "Date range overlap",
            extra={
                "conflicting_source": {"id": 5, "identifier": "upload.xml"},
                "hint": "Use confirm_overlap=true",
            },
        )
        assert err.extra is not None
        assert err.extra["conflicting_source"]["id"] == 5


class TestUnprocessableEntityError:
    def test_defaults(self):
        err = UnprocessableEntityError("Missing required sections")
        assert err.status_code == 422
        assert err.error_code == "UnprocessableEntity"

    def test_with_sections_extra(self):
        err = UnprocessableEntityError(
            "Flex Query missing sections",
            extra={
                "missing_sections": ["Trades", "CashTransactions"],
                "required_sections": ["Trades", "CashTransactions", "Transfers"],
            },
        )
        assert err.extra is not None
        assert "Trades" in err.extra["missing_sections"]
