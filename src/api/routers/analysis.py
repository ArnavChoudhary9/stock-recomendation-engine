"""`/api/v1` — deterministic analysis + recommendations endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_processing_service, get_repo
from src.api.errors import not_found, not_implemented
from src.contracts import APIResponse, StockAnalysis
from src.data.repositories.sqlite import SQLiteStockRepository
from src.processing.service import DefaultProcessingService, ProcessingError

router = APIRouter(tags=["analysis"])


@router.get(
    "/stocks/{symbol}/analysis",
    response_model=APIResponse[StockAnalysis],
)
async def get_stock_analysis(
    symbol: str,
    processing: DefaultProcessingService = Depends(get_processing_service),
) -> APIResponse[StockAnalysis]:
    """Full deterministic analysis: features, score, signals, metadata."""
    sym = symbol.strip().upper()
    try:
        analysis = await processing.analyze_stock(sym)
    except ProcessingError as e:
        raise not_found("analysis for stock", sym) from e
    return APIResponse(data=analysis)


@router.get("/recommendations", response_model=APIResponse[list[StockAnalysis]])
async def get_recommendations(
    limit: int = Query(10, gt=0, le=500),
    sector: str | None = Query(None),
    repo: SQLiteStockRepository = Depends(get_repo),
    processing: DefaultProcessingService = Depends(get_processing_service),
) -> APIResponse[list[StockAnalysis]]:
    """Rank every tracked stock (optionally filtered by sector), return top N."""
    stocks = await repo.list_symbols(sector=sector)
    if not stocks:
        return APIResponse(data=[])
    ranked = await processing.rank_stocks([s.symbol for s in stocks])
    return APIResponse(data=ranked[:limit])


@router.get("/recommendations/history")
async def recommendations_history() -> None:
    """Historical recommendation snapshots — not yet persisted."""
    raise not_implemented("recommendations history")
