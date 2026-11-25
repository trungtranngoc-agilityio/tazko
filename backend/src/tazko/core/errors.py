"""Errors for handlers, answered in the shape of .claude/rules/api-design.md.
Internal details are logged, never returned. Never change a shipped `code`:
the web app translates it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}

# Where a request value came from; dropped so `field` is just the field's name.
LOCATIONS = frozenset({"body", "query", "path", "header", "cookie"})


@dataclass(frozen=True)
class Detail:
    field: str
    message: str


class AppError(Exception):
    status = 500
    code = "INTERNAL"
    message = "internal error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        field: str | None = None,
        details: Sequence[Detail] = (),
    ) -> None:
        """`field` adds one detail for that field; a `field: ` prefix on the
        message is dropped from the detail ("slug: already taken" -> "already taken")."""
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        self.details = list(details)
        if field is not None:
            self.details.append(Detail(field, self.message.removeprefix(f"{field}: ")))


class BadRequest(AppError):
    """The request cannot be read at all. Field problems are `Invalid`."""

    status = 400
    code = "BAD_REQUEST"
    message = "bad request"


class Unauthorized(AppError):
    status = 401
    code = "UNAUTHENTICATED"
    message = "sign in required"


class Forbidden(AppError):
    status = 403
    code = "FORBIDDEN"
    message = "not allowed"


class NotFound(AppError):
    status = 404
    code = "NOT_FOUND"
    message = "not found"


class Conflict(AppError):
    """Duplicate or state conflict: slug taken, invite already used."""

    status = 409
    code = "CONFLICT"
    message = "conflict"


class Invalid(AppError):
    """A field breaks a rule (format, length, allowed values)."""

    status = 422
    code = "VALIDATION_ERROR"
    message = "invalid request"


def error_response(
    status: int, code: str, message: str, details: Sequence[Detail] = ()
) -> JSONResponse:
    body = {
        "code": code,
        "message": message,
        "details": [{"field": d.field, "message": d.message} for d in details],
    }
    return JSONResponse({"error": body}, status_code=status)


def install(app: FastAPI) -> None:
    """Map every failure to the one JSON error shape."""

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = "not found" if exc.status_code == 404 else str(exc.detail).lower()
        return error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        # A body that is not JSON, or no body at all, is a malformed request (400),
        # not a field that broke a rule (422).
        if any(err.get("type") == "json_invalid" for err in errors):
            return error_response(400, "BAD_REQUEST", "request body is not valid JSON")
        if any(
            err.get("type") == "missing" and tuple(err.get("loc", ())) == ("body",)
            for err in errors
        ):
            return error_response(400, "BAD_REQUEST", "request body is required")
        details = [
            Detail(
                ".".join(str(p) for p in err.get("loc", ()) if p not in LOCATIONS),
                str(err.get("msg", "invalid")),
            )
            for err in errors
        ]
        return error_response(422, "VALIDATION_ERROR", "invalid request", details)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        log.exception("internal error on %s %s", request.method, request.url.path)
        return error_response(500, "INTERNAL", "internal error")
