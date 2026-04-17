"""FastAPI application factory.

Use via ``uvicorn src.api.app:create_app --factory --reload``. At startup a
:class:`ServiceContainer` is built and attached to ``app.state.container``;
at shutdown the SQLite connection is closed cleanly.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Pull secrets (OPENROUTER_API_KEY, NEWSAPI_KEY, KITE_API_*) from .env at import time
# so config loaders can interpolate them. Safe no-op if the file is missing.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.api.dependencies import build_container, shutdown_container  # noqa: E402
from src.api.errors import register_exception_handlers  # noqa: E402
from src.api.middleware import install_request_id_middleware  # noqa: E402
from src.api.routers import (  # noqa: E402
    analysis_router,
    chat_router,
    kite_router,
    news_router,
    portfolio_router,
    reports_router,
    stocks_router,
    system_router,
    watchlist_router,
)
from src.config import APIConfig, load_api_config  # noqa: E402

if TYPE_CHECKING:
    from src.api.dependencies import ServiceContainer

log = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Build the FastAPI app. ``config`` override is handy for tests."""
    api_config = config or load_api_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log.info("building service container")
        container: ServiceContainer = await build_container()
        app.state.container = container
        try:
            yield
        finally:
            log.info("shutting down service container")
            await shutdown_container(container)

    app = FastAPI(
        title="Stock Intelligence API",
        version="0.1.0",
        description=(
            "Personal Indian-equity scoring + news + LLM-report API. "
            "Portfolio / Kite endpoints are stubbed pending Phase 4B."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.api.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_request_id_middleware(app, header_name=api_config.api.request_id_header)

    register_exception_handlers(app)

    app.include_router(system_router, prefix=API_PREFIX)
    app.include_router(stocks_router, prefix=API_PREFIX)
    app.include_router(analysis_router, prefix=API_PREFIX)
    app.include_router(news_router, prefix=API_PREFIX)
    app.include_router(reports_router, prefix=API_PREFIX)
    app.include_router(portfolio_router, prefix=API_PREFIX)
    app.include_router(kite_router, prefix=API_PREFIX)
    app.include_router(watchlist_router, prefix=API_PREFIX)
    app.include_router(chat_router, prefix=API_PREFIX)

    return app
