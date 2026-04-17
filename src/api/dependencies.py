"""Dependency-injection helpers + ``ServiceContainer`` for the FastAPI app.

The container is built once at app startup (inside the lifespan) and attached
to ``app.state``. Route handlers grab what they need via ``Depends(...)``.
Services missing their env keys (e.g. no ``OPENROUTER_API_KEY``) are set to
``None`` so the server still boots; endpoints that need them return 503.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Request

from src.api.errors import APIException
from src.config import (
    APIConfig,
    ConfigError,
    DataConfig,
    LLMConfig,
    NewsConfig,
    load_api_config,
    load_data_config,
    load_llm_config,
    load_news_config,
    load_processing_config,
)
from src.contracts import ScoringConfig
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.llm.providers.openrouter import OpenRouterProvider
from src.llm.service import LLMService
from src.news.service import NewsService, build_news_service
from src.processing.service import DefaultProcessingService

log = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """Bundle of live service instances shared across requests."""

    repo: SQLiteStockRepository
    data_service: DataService
    processing_service: DefaultProcessingService
    news_service: NewsService
    llm_service: LLMService | None  # None when OPENROUTER_API_KEY is missing
    data_config: DataConfig
    scoring_config: ScoringConfig
    news_config: NewsConfig
    llm_config: LLMConfig | None
    api_config: APIConfig
    started_at: datetime


async def build_container() -> ServiceContainer:
    """Load all configs, open the repo, construct every service."""
    data_cfg = load_data_config()
    scoring_cfg = load_processing_config()
    news_cfg = load_news_config()
    api_cfg = load_api_config()

    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()

    data_provider = YahooFinanceProvider(
        default_exchange=data_cfg.data.default_exchange,
        min_interval_ms=data_cfg.data.rate_limit_delay_ms,
    )
    data_service = DataService(data_provider, repo, data_cfg)
    processing_service = DefaultProcessingService(data_service, scoring_cfg)
    news_service = build_news_service(news_cfg)

    llm_service: LLMService | None = None
    llm_cfg: LLMConfig | None = None
    try:
        llm_cfg = load_llm_config()
    except ConfigError as e:
        # Usually means OPENROUTER_API_KEY isn't set — that's OK, report endpoints return 503.
        log.warning("LLM config unavailable, /reports endpoints will 503: %s", e)

    if llm_cfg is not None:
        if not llm_cfg.llm.api_key:
            log.warning("LLM api_key is empty — /reports endpoints will 503")
        else:
            provider = OpenRouterProvider(llm_cfg.llm)
            llm_service = LLMService(provider, llm_cfg)

    return ServiceContainer(
        repo=repo,
        data_service=data_service,
        processing_service=processing_service,
        news_service=news_service,
        llm_service=llm_service,
        data_config=data_cfg,
        scoring_config=scoring_cfg,
        news_config=news_cfg,
        llm_config=llm_cfg,
        api_config=api_cfg,
        started_at=datetime.now(UTC),
    )


async def shutdown_container(container: ServiceContainer) -> None:
    await container.repo.close()


# ------------------------- FastAPI dependency helpers -------------------------


def get_container(request: Request) -> ServiceContainer:
    container: ServiceContainer | None = getattr(request.app.state, "container", None)
    if container is None:
        raise APIException(
            status_code=503, code="SERVICE_UNAVAILABLE",
            message="Service container not initialised",
        )
    return container


def get_repo(container: ServiceContainer = Depends(get_container)) -> SQLiteStockRepository:
    return container.repo


def get_data_service(container: ServiceContainer = Depends(get_container)) -> DataService:
    return container.data_service


def get_processing_service(
    container: ServiceContainer = Depends(get_container),
) -> DefaultProcessingService:
    return container.processing_service


def get_news_service(container: ServiceContainer = Depends(get_container)) -> NewsService:
    return container.news_service


def get_llm_service(container: ServiceContainer = Depends(get_container)) -> LLMService:
    if container.llm_service is None:
        raise APIException(
            status_code=503, code="LLM_UNAVAILABLE",
            message="LLM is not configured — set OPENROUTER_API_KEY and restart",
        )
    return container.llm_service


def get_api_config(container: ServiceContainer = Depends(get_container)) -> APIConfig:
    return container.api_config


def get_uptime_seconds(container: ServiceContainer = Depends(get_container)) -> float:
    return (datetime.now(UTC) - container.started_at).total_seconds()


# Useful for the /health endpoint — best-effort DB ping.
async def db_status(container: ServiceContainer = Depends(get_container)) -> str:
    try:
        await container.repo.list_symbols()
        return "ok"
    except Exception as e:
        log.warning("db health probe failed: %s", e)
        return "down"


def monotonic_now() -> float:
    return time.monotonic()
