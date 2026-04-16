"""DataService — orchestrates provider + repository.

Owns the cache-first read flow: if stored data is fresh enough (per
``staleness_threshold_hours``), serve it; otherwise fetch from the provider,
upsert, then return. Missing-bar detection fills only the gap between the
latest stored date and today.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from datetime import date as DateType

from src.config import DataConfig
from src.contracts import Fundamentals, OHLCVRow, StockInfo
from src.data.providers.base import DataProvider, DataProviderError
from src.data.repositories.base import StockRepository

log = logging.getLogger(__name__)


class DataService:
    """Cache-first market data orchestrator."""

    def __init__(
        self,
        provider: DataProvider,
        repository: StockRepository,
        config: DataConfig,
    ) -> None:
        self.provider = provider
        self.repo = repository
        self.config = config

    async def get_ohlcv(
        self,
        symbol: str,
        start: DateType,
        end: DateType,
        *,
        refresh: bool = False,
    ) -> list[OHLCVRow]:
        """Return OHLCV for ``[start, end]``, auto-filling any missing tail.

        ``refresh=True`` re-fetches the full window even if stored data exists.
        """
        if refresh:
            await self._backfill(symbol, start, end)
            return await self.repo.get_ohlcv(symbol, start, end)

        latest = await self.repo.get_latest_date(symbol)
        today = _today()
        target_end = min(end, today)

        if latest is None:
            await self._backfill(symbol, start, target_end)
        elif latest < target_end and await self._is_symbol_stale(symbol):
            gap_start = latest + timedelta(days=1)
            await self._backfill(symbol, gap_start, target_end)

        return await self.repo.get_ohlcv(symbol, start, end)

    async def get_fundamentals(
        self, symbol: str, *, refresh: bool = False
    ) -> Fundamentals | None:
        if not refresh:
            cached = await self.repo.get_fundamentals(symbol)
            if cached and not self._is_stale(cached.date):
                return cached
        try:
            fresh = await self.provider.fetch_fundamentals(symbol)
        except DataProviderError as e:
            log.warning("fundamentals fetch failed for %s: %s", symbol, e)
            return await self.repo.get_fundamentals(symbol)
        await self.repo.upsert_fundamentals(symbol, fresh)
        return fresh

    async def ensure_stock(self, symbol: str) -> StockInfo | None:
        """Make sure stock metadata exists, fetching via provider if unknown."""
        existing = await self.repo.get_stock(symbol)
        if existing is not None:
            return existing
        try:
            matches = await self.provider.search_symbol(symbol)
        except DataProviderError as e:
            log.warning("stock metadata lookup failed for %s: %s", symbol, e)
            return None
        if not matches:
            return None
        info = matches[0]
        await self.repo.upsert_stock(info)
        return info

    async def refresh_symbol(self, symbol: str) -> int:
        """Fetch OHLCV + fundamentals for a single symbol. Returns bars written."""
        await self.ensure_stock(symbol)
        end = _today()
        latest = await self.repo.get_latest_date(symbol)
        start = (
            latest + timedelta(days=1)
            if latest is not None
            else end - timedelta(days=self.config.data.backfill_days)
        )
        if start > end:
            written = 0
        else:
            written = await self._backfill(symbol, start, end)
        await self.get_fundamentals(symbol, refresh=True)
        return written

    async def refresh_many(self, symbols: list[str]) -> dict[str, int]:
        """Refresh a batch of symbols sequentially.

        Per-call spacing lives in the provider (e.g. ``YahooFinanceProvider``'s
        ``_throttle``), so this method just loops and collects results.
        """
        results: dict[str, int] = {}
        for sym in symbols:
            try:
                results[sym] = await self.refresh_symbol(sym)
            except DataProviderError as e:
                log.error("refresh failed for %s: %s", sym, e)
                results[sym] = 0
        return results

    async def _backfill(
        self, symbol: str, start: DateType, end: DateType
    ) -> int:
        if start > end:
            return 0
        try:
            rows = await self.provider.fetch_ohlcv(symbol, start, end)
        except DataProviderError as e:
            log.warning("OHLCV fetch failed for %s [%s..%s]: %s", symbol, start, end, e)
            await self.repo.touch_symbol(symbol)  # record the attempt
            return 0
        if not rows:
            await self.repo.touch_symbol(symbol)
            return 0
        return await self.repo.upsert_ohlcv(symbol, rows)

    async def _is_symbol_stale(self, symbol: str) -> bool:
        """True if we haven't refreshed ``symbol`` within the staleness window."""
        last = await self.repo.last_updated(symbol)
        if last is None:
            return True
        threshold = timedelta(hours=self.config.data.staleness_threshold_hours)
        return (datetime.now(UTC) - last) > threshold

    def _is_stale(self, as_of: DateType) -> bool:
        threshold = timedelta(hours=self.config.data.staleness_threshold_hours)
        age = datetime.now(UTC) - datetime.combine(
            as_of, datetime.min.time(), tzinfo=UTC
        )
        return age > threshold


def _today() -> DateType:
    return datetime.now(UTC).date()
