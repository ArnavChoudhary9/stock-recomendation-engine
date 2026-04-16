"""Unit tests for :class:`SQLiteStockRepository`."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from src.contracts import Fundamentals, OHLCVRow, StockInfo
from src.data.repositories.sqlite import SQLiteStockRepository


def _row(symbol: str, d: date, close: float = 100.0) -> OHLCVRow:
    return OHLCVRow(
        symbol=symbol, date=d, open=close - 1, high=close + 1,
        low=close - 2, close=close, volume=1000,
    )


@pytest.mark.asyncio
async def test_upsert_and_get_ohlcv_roundtrip(sqlite_repo: SQLiteStockRepository) -> None:
    rows = [_row("TCS", date(2025, 1, d)) for d in (2, 3, 6, 7)]
    written = await sqlite_repo.upsert_ohlcv("TCS", rows)
    assert written == 4
    got = await sqlite_repo.get_ohlcv("TCS", date(2025, 1, 1), date(2025, 1, 31))
    assert [r.date for r in got] == [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6), date(2025, 1, 7)]
    assert all(r.symbol == "TCS" for r in got)


@pytest.mark.asyncio
async def test_upsert_ohlcv_is_idempotent(sqlite_repo: SQLiteStockRepository) -> None:
    rows = [_row("TCS", date(2025, 1, 2), close=100.0)]
    await sqlite_repo.upsert_ohlcv("TCS", rows)
    # Re-run with updated close — should replace, not duplicate.
    await sqlite_repo.upsert_ohlcv("TCS", [_row("TCS", date(2025, 1, 2), close=110.0)])
    got = await sqlite_repo.get_ohlcv("TCS", date(2025, 1, 1), date(2025, 1, 31))
    assert len(got) == 1
    assert got[0].close == 110.0


@pytest.mark.asyncio
async def test_get_latest_ohlcv_and_date(sqlite_repo: SQLiteStockRepository) -> None:
    await sqlite_repo.upsert_ohlcv(
        "INFY", [_row("INFY", date(2025, 1, 2)), _row("INFY", date(2025, 1, 5))]
    )
    latest = await sqlite_repo.get_latest_ohlcv("INFY")
    assert latest is not None
    assert latest.date == date(2025, 1, 5)
    assert await sqlite_repo.get_latest_date("INFY") == date(2025, 1, 5)
    assert await sqlite_repo.get_latest_ohlcv("UNKNOWN") is None
    assert await sqlite_repo.get_latest_date("UNKNOWN") is None


@pytest.mark.asyncio
async def test_upsert_ohlcv_empty_returns_zero(sqlite_repo: SQLiteStockRepository) -> None:
    assert await sqlite_repo.upsert_ohlcv("TCS", []) == 0


@pytest.mark.asyncio
async def test_upsert_and_get_fundamentals(sqlite_repo: SQLiteStockRepository) -> None:
    f = Fundamentals(
        symbol="RELIANCE", date=date(2025, 1, 15), pe=22.5,
        market_cap=15e12, roe=0.12, eps=95.0,
        debt_equity=0.35, promoter_holding=0.505, dividend_yield=0.003,
    )
    await sqlite_repo.upsert_fundamentals("RELIANCE", f)
    got = await sqlite_repo.get_fundamentals("RELIANCE")
    assert got is not None
    assert got.pe == 22.5
    assert got.market_cap == 15e12
    assert got.promoter_holding == 0.505


@pytest.mark.asyncio
async def test_get_fundamentals_returns_latest(sqlite_repo: SQLiteStockRepository) -> None:
    old = Fundamentals(symbol="TCS", date=date(2024, 12, 1), pe=20.0)
    new = Fundamentals(symbol="TCS", date=date(2025, 1, 15), pe=25.0)
    await sqlite_repo.upsert_fundamentals("TCS", old)
    await sqlite_repo.upsert_fundamentals("TCS", new)
    got = await sqlite_repo.get_fundamentals("TCS")
    assert got is not None
    assert got.pe == 25.0


@pytest.mark.asyncio
async def test_upsert_and_list_stocks(sqlite_repo: SQLiteStockRepository) -> None:
    now = datetime.now(UTC)
    a = StockInfo(symbol="TCS", name="Tata Consultancy", sector="IT",
                  industry="Software", exchange="NSE", updated_at=now)
    b = StockInfo(symbol="HDFCBANK", name="HDFC Bank", sector="Financials",
                  industry="Banks", exchange="NSE", updated_at=now)
    await sqlite_repo.upsert_stock(a)
    await sqlite_repo.upsert_stock(b)

    all_stocks = await sqlite_repo.list_symbols()
    assert [s.symbol for s in all_stocks] == ["HDFCBANK", "TCS"]

    it_only = await sqlite_repo.list_symbols(sector="IT")
    assert [s.symbol for s in it_only] == ["TCS"]


@pytest.mark.asyncio
async def test_symbol_normalised_to_upper(sqlite_repo: SQLiteStockRepository) -> None:
    await sqlite_repo.upsert_ohlcv("tcs", [_row("tcs", date(2025, 1, 2))])
    got = await sqlite_repo.get_ohlcv("TCS", date(2025, 1, 1), date(2025, 1, 10))
    assert len(got) == 1
    assert got[0].symbol == "TCS"


@pytest.mark.asyncio
async def test_init_is_idempotent(sqlite_repo: SQLiteStockRepository) -> None:
    # Calling init twice must not error (migration uses IF NOT EXISTS).
    await sqlite_repo.init()
    await sqlite_repo.init()
