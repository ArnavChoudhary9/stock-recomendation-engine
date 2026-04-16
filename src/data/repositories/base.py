"""StockRepository abstract interface.

Storage engines for OHLCV + fundamentals + stock metadata. Implementations
must be idempotent on upsert (safe to replay the same data).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as DateType
from datetime import datetime

from src.contracts import Fundamentals, OHLCVRow, StockInfo


class RepositoryError(Exception):
    """Base class for repository failures."""


class StockRepository(ABC):
    """Contract for persistent storage of market data."""

    @abstractmethod
    async def get_ohlcv(
        self, symbol: str, start: DateType, end: DateType
    ) -> list[OHLCVRow]:
        """Return OHLCV bars for ``symbol`` in ``[start, end]`` inclusive, ascending."""

    @abstractmethod
    async def get_latest_ohlcv(self, symbol: str) -> OHLCVRow | None:
        """Return the most recent OHLCV bar for ``symbol``, or ``None``."""

    @abstractmethod
    async def get_latest_date(self, symbol: str) -> DateType | None:
        """Return the most recent stored OHLCV date for ``symbol``."""

    @abstractmethod
    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        """Return the latest fundamentals snapshot for ``symbol``, or ``None``."""

    @abstractmethod
    async def upsert_ohlcv(self, symbol: str, rows: list[OHLCVRow]) -> int:
        """Insert or replace rows. Returns number of rows written."""

    @abstractmethod
    async def upsert_fundamentals(self, symbol: str, data: Fundamentals) -> None:
        """Insert or replace a fundamentals snapshot for ``symbol`` on ``data.date``."""

    @abstractmethod
    async def upsert_stock(self, info: StockInfo) -> None:
        """Insert or replace stock metadata."""

    @abstractmethod
    async def get_stock(self, symbol: str) -> StockInfo | None:
        """Return stock metadata for ``symbol``, or ``None``."""

    @abstractmethod
    async def list_symbols(self, sector: str | None = None) -> list[StockInfo]:
        """List all tracked stocks, optionally filtered by sector."""

    @abstractmethod
    async def last_updated(self, symbol: str) -> datetime | None:
        """Return the ``updated_at`` timestamp for ``symbol``, or ``None``."""

    @abstractmethod
    async def touch_symbol(self, symbol: str) -> None:
        """Bump ``stocks.updated_at`` to now — records a fetch attempt."""
