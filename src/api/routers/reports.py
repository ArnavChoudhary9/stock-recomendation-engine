"""`/api/v1/stocks/{symbol}/report` — LLM-generated stock report.

Glues ProcessingService + NewsService + LLMService together. If the LLM isn't
configured, returns 503 (see ``get_llm_service``). If the LLM is configured
but every fallback model fails at runtime, LLMService returns a degraded
:class:`StockReport` with ``degraded=True`` — we pass that through.

Reports are cached in-memory keyed by symbol so the same call within a short
window doesn't burn LLM credits; POST forces a fresh generation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_llm_service,
    get_news_service,
    get_processing_service,
)
from src.api.errors import not_found
from src.contracts import APIResponse, StockReport
from src.llm.service import LLMService
from src.news.service import NewsService
from src.processing.service import DefaultProcessingService, ProcessingError

router = APIRouter(prefix="/stocks/{symbol}", tags=["reports"])

_CACHE_TTL_SECONDS = 60 * 60  # 1 hour


@dataclass
class _ReportCacheEntry:
    report: StockReport
    stored_at: float


_cache: dict[str, _ReportCacheEntry] = {}


def _cache_fresh(entry: _ReportCacheEntry) -> bool:
    return (time.monotonic() - entry.stored_at) < _CACHE_TTL_SECONDS


async def _build_report(
    sym: str,
    processing: DefaultProcessingService,
    news_service: NewsService,
    llm: LLMService,
) -> StockReport:
    try:
        analysis = await processing.analyze_stock(sym)
    except ProcessingError as e:
        raise not_found("analysis for stock", sym) from e
    news = await news_service.get_news(sym)
    return await llm.generate_report(analysis, news)


@router.get("/report", response_model=APIResponse[StockReport])
async def get_report(
    symbol: str,
    processing: DefaultProcessingService = Depends(get_processing_service),
    news_service: NewsService = Depends(get_news_service),
    llm: LLMService = Depends(get_llm_service),
) -> APIResponse[StockReport]:
    """Return the most recent LLM report, using an in-memory TTL cache."""
    sym = symbol.strip().upper()
    cached = _cache.get(sym)
    if cached is not None and _cache_fresh(cached):
        return APIResponse(data=cached.report)

    report = await _build_report(sym, processing, news_service, llm)
    _cache[sym] = _ReportCacheEntry(report=report, stored_at=time.monotonic())
    return APIResponse(data=report)


@router.post(
    "/report",
    response_model=APIResponse[StockReport],
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_report(
    symbol: str,
    processing: DefaultProcessingService = Depends(get_processing_service),
    news_service: NewsService = Depends(get_news_service),
    llm: LLMService = Depends(get_llm_service),
) -> APIResponse[StockReport]:
    """Force a fresh LLM call, bypassing the in-memory cache."""
    sym = symbol.strip().upper()
    report = await _build_report(sym, processing, news_service, llm)
    _cache[sym] = _ReportCacheEntry(report=report, stored_at=time.monotonic())
    return APIResponse(data=report)


def clear_cache() -> None:
    """Test hook — drops the in-memory report cache."""
    _cache.clear()
