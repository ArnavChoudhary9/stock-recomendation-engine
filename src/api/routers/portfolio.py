"""`/api/v1/portfolio` and `/api/v1/kite` — Phase 4B stubs.

Every handler raises :class:`APIException` with status 501 / code
``NOT_IMPLEMENTED``. The route shapes mirror the PRD so clients and the
frontend can be built against the final API surface before Phase 4B lands.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.errors import not_implemented

portfolio_router = APIRouter(prefix="/portfolio", tags=["portfolio"])
kite_router = APIRouter(prefix="/kite", tags=["kite"])


@portfolio_router.get("/holdings")
async def list_holdings() -> None:
    raise not_implemented("portfolio holdings")


@portfolio_router.get("/positions")
async def list_positions() -> None:
    raise not_implemented("portfolio positions")


@portfolio_router.get("/overview")
async def portfolio_overview() -> None:
    raise not_implemented("portfolio overview")


@portfolio_router.get("/holdings/{symbol}")
async def holding_detail(symbol: str) -> None:
    del symbol
    raise not_implemented("portfolio holding detail")


@portfolio_router.get("/performance")
async def portfolio_performance() -> None:
    raise not_implemented("portfolio performance time-series")


@portfolio_router.get("/alerts")
async def list_alerts() -> None:
    raise not_implemented("portfolio alerts")


@portfolio_router.post("/alerts")
async def create_alert() -> None:
    raise not_implemented("portfolio alert creation")


@portfolio_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str) -> None:
    del alert_id
    raise not_implemented("portfolio alert deletion")


@kite_router.get("/auth-url")
async def kite_auth_url() -> None:
    raise not_implemented("Kite auth URL")


@kite_router.post("/callback")
async def kite_callback() -> None:
    raise not_implemented("Kite OAuth callback")


@kite_router.get("/status")
async def kite_status() -> None:
    raise not_implemented("Kite session status")
