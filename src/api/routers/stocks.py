"""`/api/v1/stocks` — static metadata, fundamentals snapshot, OHLCV, refresh."""

from __future__ import annotations

from datetime import date as DateType
from datetime import timedelta
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class BackfillRequest(BaseModel):
    """Body schema for POST /stocks/backfill.

    Either ``start_date`` or ``days`` selects the history window. If both are
    omitted, the config's ``backfill_days`` is used. If both are supplied,
    ``start_date`` wins.
    """

    model_config = ConfigDict(frozen=True)

    symbols: list[str] = Field(..., min_length=1, max_length=20)
    start_date: DateType | None = Field(
        default=None,
        description="Inclusive start date — pulls bars from this date up to today.",
    )
    days: int | None = Field(
        default=None, gt=0, le=365 * 10,
        description="Alternative to start_date: pull the last N days of history.",
    )
    force: bool = Field(
        default=False,
        description="Ignored when start_date/days are given. Otherwise forces a full "
                    "config.backfill_days window even if newer data exists.",
    )

    @field_validator("symbols")
    @classmethod
    def _upper_symbols(cls, v: list[str]) -> list[str]:
        return [s.strip().upper() for s in v if s.strip()]


class BackfillResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    written: dict[str, int] = Field(
        ..., description="Per-symbol bar count written this call (0 = empty/failed)"
    )
    total_bars: int = Field(..., ge=0)
    failed: list[str] = Field(default_factory=list)


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


@router.post(
    "/backfill",
    response_model=APIResponse[BackfillResult],
    status_code=status.HTTP_202_ACCEPTED,
)
async def backfill_stocks(
    body: BackfillRequest,
    data_service: DataService = Depends(get_data_service),
) -> APIResponse[BackfillResult]:
    """Pull OHLCV + fundamentals for a batch of symbols, optionally from a target date.

    Inline execution (no background task) because the caller usually wants the
    per-symbol bar counts back. Rate-limiting lives in the provider, so up to
    the 20-symbol cap this typically finishes within a single request window.
    Use the ``scripts/backfill.py`` CLI for larger batches.
    """
    today = datetime.now(UTC).date()
    start: DateType | None = body.start_date
    if start is None and body.days is not None:
        start = today - timedelta(days=body.days)

    written: dict[str, int] = {}
    for sym in body.symbols:
        try:
            if start is not None:
                written[sym] = await data_service.backfill_from(sym, start)
            else:
                written[sym] = await data_service.refresh_symbol(sym, refresh=body.force)
        except DataProviderError:
            written[sym] = 0

    failed = [s for s, n in written.items() if n == 0]
    return APIResponse(
        data=BackfillResult(
            written=written,
            total_bars=sum(written.values()),
            failed=failed,
        )
    )
