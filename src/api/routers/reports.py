"""`/api/v1/stocks/{symbol}/report` — LLM-generated stock report.

Glues ProcessingService + NewsService + LLMService together. If the LLM isn't
configured, returns 503 (see ``get_llm_service``). If the LLM is configured
but every fallback model fails at runtime, LLMService returns a degraded
:class:`StockReport` with ``degraded=True`` — we pass that through.

Reports are cached in SQLite keyed by a fingerprint of the analysis so the
same market state doesn't burn LLM credits on repeat requests; POST forces a
fresh generation and overwrites the stored entry.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_data_service,
    get_llm_service,
    get_news_service,
    get_processing_service,
)
from src.api.errors import not_found
from src.contracts import APIResponse, StockAnalysis, StockReport
from src.data.service import DataService
from src.llm.service import LLMService
from src.news.service import NewsService
from src.processing.service import DefaultProcessingService, ProcessingError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks/{symbol}", tags=["reports"])


def _report_cache_key(analysis: StockAnalysis) -> str:
    payload = (
        f"{analysis.metadata.config_hash}|"
        f"{analysis.timestamp.isoformat()}|"
        f"{analysis.score:.6f}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@router.get("/report", response_model=APIResponse[StockReport])
async def get_report(
    symbol: str,
    processing: DefaultProcessingService = Depends(get_processing_service),
    news_service: NewsService = Depends(get_news_service),
    llm: LLMService = Depends(get_llm_service),
    data: DataService = Depends(get_data_service),
) -> APIResponse[StockReport]:
    """Return the cached report if the analysis fingerprint matches, else generate."""
    sym = symbol.strip().upper()
    try:
        analysis = await processing.analyze_stock(sym)
    except ProcessingError as e:
        raise not_found("analysis for stock", sym) from e

    cache_key = _report_cache_key(analysis)
    cached = await data.get_cached_report(sym, cache_key)
    if cached is not None:
        try:
            return APIResponse(data=StockReport.model_validate_json(cached))
        except ValueError as e:
            log.warning("cached report for %s unreadable, regenerating: %s", sym, e)

    news = await news_service.get_news(sym)
    report = await llm.generate_report(analysis, news)
    if not report.degraded:
        await data.put_cached_report(sym, cache_key, report.model_dump_json())
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
    data: DataService = Depends(get_data_service),
) -> APIResponse[StockReport]:
    """Force a fresh LLM call, bypassing the cache and overwriting on success."""
    sym = symbol.strip().upper()
    try:
        analysis = await processing.analyze_stock(sym)
    except ProcessingError as e:
        raise not_found("analysis for stock", sym) from e
    news = await news_service.get_news(sym)
    report = await llm.generate_report(analysis, news)
    if not report.degraded:
        await data.put_cached_report(
            sym, _report_cache_key(analysis), report.model_dump_json()
        )
    return APIResponse(data=report)


def clear_cache() -> None:
    """Test hook — retained for backward compat; the cache now lives in the DB."""
    return None
