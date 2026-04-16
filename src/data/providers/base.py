"""DataProvider abstract interface.

Pluggable market-data source. All implementations must translate external
data into the shared contracts in :mod:`src.contracts.data`. Provider code
must never import from repositories or services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as DateType

from src.contracts import Fundamentals, OHLCVRow, StockInfo


class DataProviderError(Exception):
    """Base class for provider-level failures."""


class SymbolNotFoundError(DataProviderError):
    """Symbol is not listed or unknown to the upstream source."""


class RateLimitedError(DataProviderError):
    """Upstream throttled the request."""


class DataProvider(ABC):
    """Contract for external market-data sources."""

    name: str

    @abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, start: DateType, end: DateType
    ) -> list[OHLCVRow]:
        """Return daily OHLCV bars for ``symbol`` in ``[start, end]`` (inclusive)."""

    @abstractmethod
    async def fetch_fundamentals(self, symbol: str) -> Fundamentals:
        """Return the latest fundamentals snapshot for ``symbol``."""

    @abstractmethod
    async def search_symbol(self, query: str) -> list[StockInfo]:
        """Free-text symbol search. Empty list means no match."""
