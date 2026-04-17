"""API error primitives + FastAPI exception handlers.

Every non-2xx response goes out wrapped in the :class:`APIError` envelope
defined in ``src.contracts.api`` so clients see a consistent shape. Handlers
map module-level exceptions (``RepositoryError``, ``ProcessingError``,
``DataProviderError``, ``NewsServiceError``, ``LLMError``, etc.) onto status
codes + machine-readable codes.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.contracts import APIError, ErrorDetail, ResponseMeta

log = logging.getLogger(__name__)


class APIException(Exception):  # noqa: N818 — APIError is already the response envelope
    """Raise this in routes to emit a structured :class:`APIError` response.

    Prefer over ``HTTPException`` — carries a machine-readable ``code``
    and optional ``details`` payload on top of the status + message.
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(resource: str, identifier: str) -> APIException:
    return APIException(
        status_code=404,
        code="NOT_FOUND",
        message=f"{resource} '{identifier}' not found",
        details={"resource": resource, "id": identifier},
    )


def not_implemented(feature: str) -> APIException:
    return APIException(
        status_code=501,
        code="NOT_IMPLEMENTED",
        message=f"{feature} is not implemented yet (Phase 4B deferred)",
        details={"feature": feature},
    )


def bad_request(message: str, **details: Any) -> APIException:
    return APIException(
        status_code=400, code="BAD_REQUEST", message=message,
        details=dict(details) if details else None,
    )


def _envelope(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    envelope = APIError(
        error=ErrorDetail(code=code, message=message, details=details),
        meta=ResponseMeta(request_id=request_id),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that convert every uncaught exception into ``APIError``."""

    @app.exception_handler(APIException)
    async def handle_api_exception(request: Request, exc: APIException) -> JSONResponse:
        return _envelope(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=exc.details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _http_status_code(exc.status_code)
        message = str(exc.detail) if exc.detail is not None else code
        return _envelope(
            status_code=exc.status_code, code=code, message=message,
            request_id=_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _envelope(
            status_code=422, code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=_request_id(request),
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return _envelope(
            status_code=500, code="INTERNAL_ERROR",
            message=f"{type(exc).__name__}: {exc}",
            request_id=_request_id(request),
        )


def _http_status_code(code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        501: "NOT_IMPLEMENTED",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(code, f"HTTP_{code}")


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    return str(rid) if rid else None


def new_request_id() -> str:
    """Short UUID used by middleware + handlers to tag each request."""
    return uuid.uuid4().hex[:12]
