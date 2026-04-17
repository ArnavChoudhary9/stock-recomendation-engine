"""Request-scoped middleware.

Attaches a short request-id to ``request.state`` (and echoes it back in the
response header) so exception envelopes and logs can be correlated. Registered
via ``install_request_id_middleware`` rather than ``add_middleware`` to sidestep
Starlette's strict ``_MiddlewareFactory`` protocol typing around custom kwargs.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from src.api.errors import new_request_id


def install_request_id_middleware(app: FastAPI, *, header_name: str = "X-Request-ID") -> None:
    """Attach an HTTP middleware that assigns + echoes a request-id header."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        incoming = request.headers.get(header_name)
        request.state.request_id = incoming or new_request_id()
        response: Response = await call_next(request)
        response.headers[header_name] = request.state.request_id
        return response
