"""Integration tests for the data pipeline: fetch → store → query round-trip.

These use a real on-disk SQLite DB and the fake provider. The network
``yfinance`` path is covered by a separate, opt-in test gated behind an env
flag — CI/local runs shouldn't touch the internet.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.config import DataConfig, DataProviderConfig, StorageConfig
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.scheduler.jobs import refresh_all_symbols
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_full_pipeline_fetch_store_query(tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()

    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        provider.seed_ohlcv("TCS", today - timedelta(days=30), days=30)
        provider.seed_fundamentals("TCS")
        provider.seed_stock("TCS", name="Tata Consultancy", sector="IT")

        cfg = DataConfig(
            data=DataProviderConfig(
                provider="fake", backfill_days=30, rate_limit_delay_ms=0,
            ),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        service = DataService(provider, repo, cfg)

        written = await service.refresh_symbol("TCS")
        assert written > 0

        # Query back via repo.
        rows = await repo.get_ohlcv("TCS", today - timedelta(days=30), today)
        assert rows == sorted(rows, key=lambda r: r.date)
        assert len(rows) > 0

        fundamentals = await repo.get_fundamentals("TCS")
        assert fundamentals is not None
        assert fundamentals.pe is not None

        info = await repo.get_stock("TCS")
        assert info is not None and info.sector == "IT"
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_db_persists_across_connections(tmp_path: Path) -> None:
    db_path = tmp_path / "persist.db"
    today = datetime.now(UTC).date()

    repo1 = SQLiteStockRepository(db_path, wal_mode=False)
    await repo1.init()
    provider = FakeProvider()
    provider.seed_ohlcv("INFY", today - timedelta(days=10), days=10)
    cfg = DataConfig(
        data=DataProviderConfig(provider="fake", backfill_days=10, rate_limit_delay_ms=0),
        storage=StorageConfig(path=db_path, wal_mode=False),
    )
    service = DataService(provider, repo1, cfg)
    await service.get_ohlcv("INFY", today - timedelta(days=10), today)
    await repo1.close()

    # Reopen — data should still be there.
    repo2 = SQLiteStockRepository(db_path, wal_mode=False)
    await repo2.init()
    try:
        rows = await repo2.get_ohlcv("INFY", today - timedelta(days=10), today)
        assert len(rows) > 0
    finally:
        await repo2.close()


@pytest.mark.asyncio
async def test_scheduler_refresh_all_symbols_pulls_tracked(tmp_path: Path) -> None:
    db_path = tmp_path / "sched.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        for sym in ("TCS", "INFY"):
            provider.seed_ohlcv(sym, today - timedelta(days=5), days=5)
            provider.seed_fundamentals(sym)
            info = provider.seed_stock(sym, sector="IT")
            await repo.upsert_stock(info)

        cfg = DataConfig(
            data=DataProviderConfig(provider="fake", backfill_days=5, rate_limit_delay_ms=0),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        service = DataService(provider, repo, cfg)
        results = await refresh_all_symbols(service)
        assert set(results.keys()) == {"TCS", "INFY"}
        for sym in ("TCS", "INFY"):
            assert results[sym] > 0
    finally:
        await repo.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS") != "1",
    reason="Opt-in: set RUN_NETWORK_TESTS=1 to hit Yahoo Finance",
)
async def test_yahoo_live_fetch(tmp_path: Path) -> None:
    repo = SQLiteStockRepository(tmp_path / "yahoo.db", wal_mode=False)
    await repo.init()
    try:
        cfg = DataConfig(
            data=DataProviderConfig(provider="yahoo", backfill_days=10, rate_limit_delay_ms=0),
            storage=StorageConfig(path=tmp_path / "yahoo.db", wal_mode=False),
        )
        service = DataService(YahooFinanceProvider(), repo, cfg)
        end = datetime.now(UTC).date()
        start = end - timedelta(days=10)
        rows = await service.get_ohlcv("RELIANCE", start, end)
        assert len(rows) > 0
    finally:
        await repo.close()
