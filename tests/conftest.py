"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load .env at collection time so tests that read env vars (e.g. NEWSAPI_KEY)
# pick them up without requiring the user to export them per-shell.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.config import DataConfig, DataProviderConfig, StorageConfig  # noqa: E402
from src.contracts import Fundamentals, OHLCVRow, StockInfo  # noqa: E402
from src.data.providers.base import DataProvider  # noqa: E402
from src.data.repositories.sqlite import SQLiteStockRepository  # noqa: E402


class FakeProvider(DataProvider):
    """In-memory provider for tests. Returns deterministic data per symbol."""

    name = "fake"

    def __init__(self) -> None:
        self.ohlcv: dict[str, list[OHLCVRow]] = {}
        self.fundamentals: dict[str, Fundamentals] = {}
        self.stocks: dict[str, StockInfo] = {}
        self.fetch_calls: list[tuple[str, date, date]] = []

    def seed_ohlcv(self, symbol: str, start: date, days: int) -> list[OHLCVRow]:
        rows = []
        for i in range(days):
            d = start + timedelta(days=i)
            # weekday-only bars, mimicking real market data
            if d.weekday() >= 5:
                continue
            price = 100.0 + i
            rows.append(
                OHLCVRow(
                    symbol=symbol, date=d, open=price, high=price + 2,
                    low=price - 1, close=price + 1, volume=1000 + i,
                )
            )
        self.ohlcv.setdefault(symbol.upper(), []).extend(rows)
        return rows

    def seed_fundamentals(self, symbol: str, **kwargs: float) -> Fundamentals:
        f = Fundamentals(
            symbol=symbol,
            date=date.today(),
            pe=kwargs.get("pe", 25.0),
            market_cap=kwargs.get("market_cap", 1_000_000_000.0),
            roe=kwargs.get("roe", 0.18),
            eps=kwargs.get("eps", 50.0),
            debt_equity=kwargs.get("debt_equity", 0.5),
            promoter_holding=kwargs.get("promoter_holding", 0.55),
            dividend_yield=kwargs.get("dividend_yield", 0.02),
        )
        self.fundamentals[symbol.upper()] = f
        return f

    def seed_stock(self, symbol: str, name: str = "", sector: str = "IT") -> StockInfo:
        info = StockInfo(
            symbol=symbol,
            name=name or symbol,
            sector=sector,
            industry="Software",
            exchange="NSE",
            updated_at=datetime.now(UTC),
        )
        self.stocks[symbol.upper()] = info
        return info

    async def fetch_ohlcv(
        self, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        self.fetch_calls.append((symbol.upper(), start, end))
        bars = self.ohlcv.get(symbol.upper(), [])
        return [r for r in bars if start <= r.date <= end]

    async def fetch_fundamentals(self, symbol: str) -> Fundamentals:
        f = self.fundamentals.get(symbol.upper())
        if f is None:
            raise KeyError(symbol)
        return f

    async def search_symbol(self, query: str) -> list[StockInfo]:
        s = self.stocks.get(query.upper())
        return [s] if s else []


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest_asyncio.fixture
async def sqlite_repo(tmp_path: Path) -> AsyncIterator[SQLiteStockRepository]:
    repo = SQLiteStockRepository(tmp_path / "test.db", wal_mode=False)
    await repo.init()
    try:
        yield repo
    finally:
        await repo.close()


@pytest.fixture
def data_config(tmp_path: Path) -> DataConfig:
    return DataConfig(
        data=DataProviderConfig(
            provider="fake",
            staleness_threshold_hours=24,
            backfill_days=30,
            batch_size=10,
            rate_limit_delay_ms=0,
        ),
        storage=StorageConfig(path=tmp_path / "test.db", wal_mode=False),
    )
