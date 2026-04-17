"""`/api/v1/stocks/{symbol}/news` — news bundle with sentiment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_news_service, get_repo
from src.contracts import APIResponse, NewsBundle
from src.data.repositories.sqlite import SQLiteStockRepository
from src.news.service import NewsService

router = APIRouter(prefix="/stocks/{symbol}", tags=["news"])


@router.get("/news", response_model=APIResponse[NewsBundle])
async def get_stock_news(
    symbol: str,
    refresh: bool = Query(False, description="Bypass TTL cache and fetch fresh"),
    news_service: NewsService = Depends(get_news_service),
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[NewsBundle]:
    """Return deduplicated, sentiment-scored news for ``symbol``.

    Uses the stock's company name from the repo (if tracked) to improve
    provider recall, and the NewsService TTL cache to avoid hammering
    upstream APIs. Provider failures degrade to an empty bundle — never raise.
    """
    sym = symbol.strip().upper()
    info = await repo.get_stock(sym)
    company_name = info.name if info else None
    bundle = await news_service.get_news(sym, company_name=company_name, refresh=refresh)
    return APIResponse(data=bundle)
