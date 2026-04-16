"""API layer envelope contracts: success and error response wrappers.

All HTTP responses follow:
    success → { "data": ..., "meta": { "timestamp": ..., "version": ... } }
    error   → { "error": { "code": ..., "message": ..., "details": ... } }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

API_VERSION = "v1"

T = TypeVar("T")


class ResponseMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = API_VERSION
    request_id: str | None = None


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope. Use ``APIResponse[StockAnalysis]`` etc. in routers."""

    data: T
    meta: ResponseMeta = Field(default_factory=lambda: ResponseMeta.model_validate({}))


class ErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Machine-readable error code, e.g. 'STOCK_NOT_FOUND'")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = None


class APIError(BaseModel):
    """Standard error envelope returned with non-2xx status codes."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=lambda: ResponseMeta.model_validate({}))


class PaginationMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int = Field(..., ge=0)
    limit: int = Field(..., gt=0)
    offset: int = Field(..., ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for list endpoints that need pagination metadata."""

    data: list[T]
    pagination: PaginationMeta
    meta: ResponseMeta = Field(default_factory=lambda: ResponseMeta.model_validate({}))


class HealthStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str = Field(..., description="ok | degraded | down")
    components: dict[str, str] = Field(
        default_factory=dict, description="Per-subsystem status, e.g. {'db': 'ok', 'kite': 'down'}"
    )
    uptime_seconds: float = Field(..., ge=0)
