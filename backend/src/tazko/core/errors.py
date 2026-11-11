"""One error type for handlers. Internal details are logged, never returned.

Every error body is `{"error": "<message>"}`; frontend/src/shared/api/client.ts reads it.

Note: a board the caller may not see answers `NotFound`, not `Forbidden`,
so restricted boards do not leak their existence (KNOWN-DEVIATIONS #1).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    status = 500
    message = "internal error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message


class NotFound(AppError):
    status = 404
    message = "not found"


class Unauthorized(AppError):
    status = 401
    message = "sign in required"


class Forbidden(AppError):
    status = 403
    message = "not allowed"


class BadRequest(AppError):
    status = 400
    message = "bad request"


def error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def install(app: FastAPI) -> None:
    """Map every failure to the one JSON error shape."""

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = "not found" if exc.status_code == 404 else str(exc.detail).lower()
        return error_response(exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        return error_response(400, f"{where}: {first.get('msg', 'invalid')}".strip(": "))

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        log.exception("internal error on %s %s", request.method, request.url.path)
        return error_response(500, "internal error")
