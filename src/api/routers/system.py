"""`/api/v1` — health, config, and pipeline-run endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import (
    ServiceContainer,
    db_status,
    get_container,
    get_uptime_seconds,
)
from src.contracts import APIResponse, HealthStatus

router = APIRouter(tags=["system"])


class ConfigSnapshot(BaseModel):
    """Non-sensitive view of the active runtime config."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]
    processing: dict[str, Any]
    news: dict[str, Any]
    llm: dict[str, Any] | None
    api: dict[str, Any]


class PipelineRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scheduled: bool
    symbols_count: int
    message: str


@router.get("/health", response_model=APIResponse[HealthStatus])
async def health(
    uptime: float = Depends(get_uptime_seconds),
    db: str = Depends(db_status),
    container: ServiceContainer = Depends(get_container),
) -> APIResponse[HealthStatus]:
    components = {
        "db": db,
        "llm": "ok" if container.llm_service is not None else "unconfigured",
        "news": "ok",
    }
    status = "ok" if db == "ok" else "degraded"
    return APIResponse(
        data=HealthStatus(status=status, components=components, uptime_seconds=uptime)
    )


@router.get("/config", response_model=APIResponse[ConfigSnapshot])
async def active_config(
    container: ServiceContainer = Depends(get_container),
) -> APIResponse[ConfigSnapshot]:
    """Return the currently loaded config with secrets masked."""
    data_dump = container.data_config.model_dump(mode="json")
    processing_dump = container.scoring_config.model_dump(mode="json")
    news_dump = container.news_config.model_dump(mode="json")
    api_dump = container.api_config.model_dump(mode="json")

    llm_dump: dict[str, Any] | None = None
    if container.llm_config is not None:
        llm_dump = container.llm_config.model_dump(mode="json")
        # Mask the API key — it's present in the loaded config after env interpolation.
        if "llm" in llm_dump and "api_key" in llm_dump["llm"]:
            llm_dump["llm"]["api_key"] = _mask(llm_dump["llm"]["api_key"])

    return APIResponse(
        data=ConfigSnapshot(
            data=data_dump, processing=processing_dump, news=news_dump,
            llm=llm_dump, api=api_dump,
        )
    )


@router.post("/pipeline/run", response_model=APIResponse[PipelineRunResult])
async def run_pipeline(
    background: BackgroundTasks,
    container: ServiceContainer = Depends(get_container),
) -> APIResponse[PipelineRunResult]:
    """Kick off a full data refresh across every tracked symbol in the background.

    Returns immediately — check `/health` or the logs for progress.
    """
    stocks = await container.repo.list_symbols()
    symbols = [s.symbol for s in stocks]
    background.add_task(_run_refresh, container, symbols)
    return APIResponse(
        data=PipelineRunResult(
            scheduled=True,
            symbols_count=len(symbols),
            message=f"refresh queued for {len(symbols)} symbols",
        )
    )


async def _run_refresh(container: ServiceContainer, symbols: list[str]) -> None:
    if not symbols:
        return
    await container.data_service.refresh_many(symbols)


def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 6:
        return "***"
    return f"{secret[:3]}…{secret[-3:]}"
