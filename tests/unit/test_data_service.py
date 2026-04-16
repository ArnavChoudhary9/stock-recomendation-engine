"""Unit tests for :class:`DataService` using a fake provider + SQLite repo."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.config import DataConfig
from src.contracts import Fundamentals, OHLCVRow
from src.data.providers.base import DataProviderError
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_get_ohlcv_fetches_on_empty_cache(
    fake_provider: FakeProvider, sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    today = datetime.now(UTC).date()
    fake_provider.seed_ohlcv("TCS", today - timedelta(days=10), days=10)
    service = DataService(fake_provider, sqlite_repo, data_config)

    rows = await service.get_ohlcv("TCS", today - timedelta(days=10), today)
    assert len(rows) > 0
    assert len(fake_provider.fetch_calls) == 1  # fetched once
    # Re-query: should be served from cache.
    rows2 = await service.get_ohlcv("TCS", today - timedelta(days=10), today)
    assert len(rows2) == len(rows)
    assert len(fake_provider.fetch_calls) == 1  # no extra fetch


@pytest.mark.asyncio
async def test_get_ohlcv_fills_gap_only(
    fake_provider: FakeProvider, sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    today = datetime.now(UTC).date()
    old_start = today - timedelta(days=20)
    fake_provider.seed_ohlcv("TCS", old_start, days=20)
    service = DataService(fake_provider, sqlite_repo, data_config)

    # Pre-seed first 10 days in the repo directly.
    first_10 = [r for r in fake_provider.ohlcv["TCS"] if r.date <= old_start + timedelta(days=9)]
    await sqlite_repo.upsert_ohlcv("TCS", first_10)

    await service.get_ohlcv("TCS", old_start, today)
    # Exactly one gap-fill fetch, starting after the latest stored date.
    assert len(fake_provider.fetch_calls) == 1
    fetch_start = fake_provider.fetch_calls[0][1]
    assert fetch_start > first_10[-1].date


@pytest.mark.asyncio
async def test_refresh_true_forces_fetch(
    fake_provider: FakeProvider, sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    today = datetime.now(UTC).date()
    fake_provider.seed_ohlcv("TCS", today - timedelta(days=5), days=5)
    service = DataService(fake_provider, sqlite_repo, data_config)

    await service.get_ohlcv("TCS", today - timedelta(days=5), today)
    await service.get_ohlcv("TCS", today - timedelta(days=5), today, refresh=True)
    assert len(fake_provider.fetch_calls) == 2


@pytest.mark.asyncio
async def test_get_fundamentals_cache_then_refresh(
    fake_provider: FakeProvider, sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    fake_provider.seed_fundamentals("TCS", pe=30.0)
    service = DataService(fake_provider, sqlite_repo, data_config)

    first = await service.get_fundamentals("TCS")
    assert first is not None and first.pe == 30.0
    cached = await sqlite_repo.get_fundamentals("TCS")
    assert cached is not None and cached.pe == 30.0

    fake_provider.seed_fundamentals("TCS", pe=35.0)
    cached_again = await service.get_fundamentals("TCS")  # still fresh → cache
    assert cached_again is not None and cached_again.pe == 30.0

    refreshed = await service.get_fundamentals("TCS", refresh=True)
    assert refreshed is not None and refreshed.pe == 35.0


@pytest.mark.asyncio
async def test_get_fundamentals_falls_back_on_provider_error(
    sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    class BrokenProvider(FakeProvider):
        async def fetch_fundamentals(self, symbol: str) -> Fundamentals:
            raise DataProviderError("boom")

    p = BrokenProvider()
    # Pre-seed the repo so we have something to fall back to.
    await sqlite_repo.upsert_fundamentals(
        "TCS", Fundamentals(symbol="TCS", date=date(2020, 1, 1), pe=10.0)
    )
    service = DataService(p, sqlite_repo, data_config)
    got = await service.get_fundamentals("TCS", refresh=True)
    assert got is not None and got.pe == 10.0


@pytest.mark.asyncio
async def test_ensure_stock_persists_metadata(
    fake_provider: FakeProvider, sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    fake_provider.seed_stock("TCS", name="Tata Consultancy", sector="IT")
    service = DataService(fake_provider, sqlite_repo, data_config)

    info = await service.ensure_stock("TCS")
    assert info is not None and info.name == "Tata Consultancy"
    stored = await sqlite_repo.get_stock("TCS")
    assert stored is not None and stored.sector == "IT"


@pytest.mark.asyncio
async def test_refresh_many_continues_on_failure(
    sqlite_repo: SQLiteStockRepository, data_config: DataConfig
) -> None:
    class PartialProvider(FakeProvider):
        async def fetch_ohlcv(self, symbol: str, start: date, end: date) -> list[OHLCVRow]:
            if symbol.upper() == "FAIL":
                raise DataProviderError("nope")
            return await super().fetch_ohlcv(symbol, start, end)

        async def fetch_fundamentals(self, symbol: str) -> Fundamentals:
            if symbol.upper() == "FAIL":
                raise DataProviderError("nope")
            return await super().fetch_fundamentals(symbol)

    today = datetime.now(UTC).date()
    p = PartialProvider()
    p.seed_ohlcv("TCS", today - timedelta(days=5), days=5)
    p.seed_fundamentals("TCS")
    p.seed_stock("TCS")

    service = DataService(p, sqlite_repo, data_config)
    results = await service.refresh_many(["TCS", "FAIL"])
    assert results["TCS"] > 0
    assert results["FAIL"] == 0
