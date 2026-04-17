"""`/api/v1/watchlist` — curated list of symbols the user wants to follow.

Watching a symbol is orthogonal to the tracked-stocks table: adding here
doesn't backfill OHLCV. Use ``POST /stocks/{symbol}/refresh`` to pull data,
or `GET /watchlist/analysis` to rank everything on the list using whatever
history is already in the repo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_processing_service, get_repo
from src.api.errors import not_found
from src.contracts import (
    AddToWatchlistRequest,
    APIResponse,
    StockAnalysis,
    WatchlistItem,
)
from src.data.repositories.sqlite import SQLiteStockRepository
from src.processing.service import DefaultProcessingService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=APIResponse[list[WatchlistItem]])
async def list_watchlist(
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[list[WatchlistItem]]:
    items = await repo.list_watchlist()
    return APIResponse(data=items)


@router.post(
    "",
    response_model=APIResponse[WatchlistItem],
    status_code=status.HTTP_201_CREATED,
)
async def add_to_watchlist(
    body: AddToWatchlistRequest,
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[WatchlistItem]:
    item = await repo.add_to_watchlist(body.symbol, notes=body.notes)
    return APIResponse(data=item)


@router.get("/{symbol}", response_model=APIResponse[WatchlistItem])
async def get_watchlist_item(
    symbol: str,
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[WatchlistItem]:
    sym = symbol.strip().upper()
    item = await repo.get_watchlist_item(sym)
    if item is None:
        raise not_found("watchlist entry", sym)
    return APIResponse(data=item)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    repo: SQLiteStockRepository = Depends(get_repo),
) -> None:
    sym = symbol.strip().upper()
    removed = await repo.remove_from_watchlist(sym)
    if not removed:
        raise not_found("watchlist entry", sym)


@router.get("/analysis/ranked", response_model=APIResponse[list[StockAnalysis]])
async def analyze_watchlist(
    repo: SQLiteStockRepository = Depends(get_repo),
    processing: DefaultProcessingService = Depends(get_processing_service),
) -> APIResponse[list[StockAnalysis]]:
    """Score every symbol currently on the watchlist; skip ones lacking data."""
    items = await repo.list_watchlist()
    if not items:
        return APIResponse(data=[])
    ranked = await processing.rank_stocks([i.symbol for i in items])
    return APIResponse(data=ranked)
