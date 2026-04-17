"""`/api/v1/stocks` — static metadata, fundamentals snapshot, OHLCV, refresh."""

from __future__ import annotations

from datetime import date as DateType
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_data_service, get_repo
from src.api.errors import bad_request, not_found
from src.contracts import (
    APIResponse,
    Fundamentals,
    OHLCVRow,
    PaginatedResponse,
    PaginationMeta,
    StockInfo,
)
from src.data.providers.base import DataProviderError
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockDetail(BaseModel):
    """Stock info + latest fundamentals + latest close, returned by GET /stocks/{symbol}."""

    model_config = ConfigDict(frozen=True)

    info: StockInfo
    fundamentals: Fundamentals | None = None
    latest_close: float | None = None
    latest_date: DateType | None = None


class RefreshResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    bars_written: int


@router.get("", response_model=PaginatedResponse[StockInfo])
async def list_stocks(
    sector: str | None = Query(None),
    limit: int = Query(100, gt=0, le=1000),
    offset: int = Query(0, ge=0),
    repo: SQLiteStockRepository = Depends(get_repo),
) -> PaginatedResponse[StockInfo]:
    """List tracked stocks, optionally filtered by sector."""
    all_stocks = await repo.list_symbols(sector=sector)
    total = len(all_stocks)
    page = all_stocks[offset : offset + limit]
    return PaginatedResponse(
        data=page,
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/{symbol}", response_model=APIResponse[StockDetail])
async def get_stock(
    symbol: str,
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[StockDetail]:
    """Return static info + latest fundamentals snapshot for a tracked stock."""
    sym = symbol.strip().upper()
    info = await repo.get_stock(sym)
    if info is None:
        raise not_found("stock", sym)
    fundamentals = await repo.get_fundamentals(sym)
    latest = await repo.get_latest_ohlcv(sym)
    return APIResponse(
        data=StockDetail(
            info=info,
            fundamentals=fundamentals,
            latest_close=latest.close if latest else None,
            latest_date=latest.date if latest else None,
        )
    )


@router.get("/{symbol}/ohlcv", response_model=APIResponse[list[OHLCVRow]])
async def get_stock_ohlcv(
    symbol: str,
    start: DateType | None = Query(None, description="Inclusive start date (ISO)"),
    end: DateType | None = Query(None, description="Inclusive end date (ISO)"),
    days: int = Query(
        365, gt=0, le=365 * 10,
        description="If start/end omitted, return trailing N days up to today",
    ),
    repo: SQLiteStockRepository = Depends(get_repo),
) -> APIResponse[list[OHLCVRow]]:
    sym = symbol.strip().upper()
    if start is None or end is None:
        latest = await repo.get_latest_date(sym)
        end_date = end or latest or DateType.today()
        start_date = start or (end_date - timedelta(days=days))
    else:
        start_date = start
        end_date = end
    if start_date > end_date:
        raise bad_request(
            "start must be on or before end",
            start=start_date.isoformat(), end=end_date.isoformat(),
        )
    rows = await repo.get_ohlcv(sym, start_date, end_date)
    return APIResponse(data=rows)


@router.post(
    "/{symbol}/refresh",
    response_model=APIResponse[RefreshResult],
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_stock(
    symbol: str,
    data_service: DataService = Depends(get_data_service),
) -> APIResponse[RefreshResult]:
    """Trigger a data fetch for ``symbol``. Returns bars written."""
    sym = symbol.strip().upper()
    try:
        written = await data_service.refresh_symbol(sym)
    except DataProviderError as e:
        raise bad_request(f"provider refresh failed: {e}", symbol=sym) from e
    return APIResponse(data=RefreshResult(symbol=sym, bars_written=written))
