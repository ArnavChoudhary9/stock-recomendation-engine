"""Yahoo Finance data provider (via ``yfinance``).

Indian equities on Yahoo are suffixed by exchange: ``RELIANCE`` → ``RELIANCE.NS``
for NSE, ``RELIANCE.BO`` for BSE. Provider translates internal symbols by
appending the suffix derived from ``exchange``. ``yfinance`` is a sync library,
so we wrap calls in :func:`asyncio.to_thread` to stay non-blocking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from datetime import date as DateType
from typing import Any

from src.contracts import Fundamentals, OHLCVRow, StockInfo
from src.data.providers.base import (
    DataProvider,
    DataProviderError,
    SymbolNotFoundError,
)

log = logging.getLogger(__name__)

_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance provider (free, no API key). ``yfinance`` must be installed.

    A process-wide async lock + minimum-interval gate spaces every outbound
    call (history, info, search) so bulk operations can't burst past Yahoo's
    rate limits.
    """

    name = "yahoo"

    def __init__(
        self, default_exchange: str = "NSE", *, min_interval_ms: int = 500
    ) -> None:
        self.default_exchange = default_exchange
        self.min_interval_s = max(0.0, min_interval_ms / 1000.0)
        self._gate = asyncio.Lock()
        self._last_call_t: float = 0.0

    async def _throttle(self) -> None:
        """Block until ``min_interval_s`` has elapsed since the last call."""
        if self.min_interval_s <= 0:
            return
        async with self._gate:
            now = time.monotonic()
            wait = self.min_interval_s - (now - self._last_call_t)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call_t = time.monotonic()

    def _yahoo_ticker(self, symbol: str, exchange: str | None = None) -> str:
        sym = symbol.strip().upper()
        # Index tickers (e.g. ^NSEI, ^BSESN) and already-qualified tickers pass through.
        if sym.startswith("^") or "." in sym:
            return sym
        suffix = _SUFFIX.get((exchange or self.default_exchange).upper(), ".NS")
        return f"{sym}{suffix}"

    async def fetch_ohlcv(
        self, symbol: str, start: DateType, end: DateType
    ) -> list[OHLCVRow]:
        if start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")
        ticker = self._yahoo_ticker(symbol)

        def _fetch() -> list[OHLCVRow]:
            import yfinance as yf

            t = yf.Ticker(ticker)
            df = t.history(
                start=start.isoformat(),
                end=(end.fromordinal(end.toordinal() + 1)).isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=False,
            )
            if df is None or df.empty:
                return []
            rows: list[OHLCVRow] = []
            for idx, r in df.iterrows():
                d = _to_date(idx)
                if d is None:
                    continue
                try:
                    rows.append(
                        OHLCVRow(
                            symbol=symbol,
                            date=d,
                            open=float(r["Open"]),
                            high=float(r["High"]),
                            low=float(r["Low"]),
                            close=float(r["Close"]),
                            volume=int(r["Volume"]),
                        )
                    )
                except (ValueError, KeyError, TypeError) as e:
                    log.debug("skip malformed bar for %s on %s: %s", symbol, d, e)
            return rows

        await self._throttle()
        try:
            return await asyncio.to_thread(_fetch)
        except ImportError:
            raise
        except Exception as e:
            raise DataProviderError(f"Yahoo OHLCV fetch failed for {symbol}: {e}") from e

    async def fetch_fundamentals(self, symbol: str) -> Fundamentals:
        ticker = self._yahoo_ticker(symbol)

        def _fetch() -> dict[str, Any]:
            import yfinance as yf

            t = yf.Ticker(ticker)
            info = t.info or {}
            if not info or info.get("regularMarketPrice") is None:
                raise SymbolNotFoundError(f"Yahoo has no data for {ticker}")
            return info

        await self._throttle()
        try:
            info = await asyncio.to_thread(_fetch)
        except SymbolNotFoundError:
            raise
        except Exception as e:
            raise DataProviderError(f"Yahoo fundamentals fetch failed for {symbol}: {e}") from e

        return Fundamentals(
            symbol=symbol,
            date=datetime.now(UTC).date(),
            pe=_safe_float(info.get("trailingPE")),
            market_cap=_safe_float(info.get("marketCap")),
            roe=_safe_float(info.get("returnOnEquity")),
            eps=_safe_float(info.get("trailingEps")),
            debt_equity=_safe_ratio(info.get("debtToEquity")),
            promoter_holding=None,
            dividend_yield=_safe_float(info.get("dividendYield")),
        )

    async def search_symbol(self, query: str) -> list[StockInfo]:
        ticker = self._yahoo_ticker(query)

        def _fetch() -> StockInfo | None:
            import yfinance as yf

            t = yf.Ticker(ticker)
            info = t.info or {}
            if not info or not info.get("symbol"):
                return None
            return StockInfo(
                symbol=query.strip().upper(),
                name=info.get("longName") or info.get("shortName") or query,
                sector=info.get("sector"),
                industry=info.get("industry"),
                exchange="BSE" if ticker.endswith(".BO") else "NSE",
                updated_at=datetime.now(UTC),
            )

        await self._throttle()
        try:
            result = await asyncio.to_thread(_fetch)
        except Exception as e:
            raise DataProviderError(f"Yahoo search failed for {query}: {e}") from e
        return [result] if result else []


def _to_date(idx: Any) -> DateType | None:
    """Coerce a pandas index label (Timestamp/datetime/date/str) to ``date``."""
    if isinstance(idx, DateType) and not isinstance(idx, datetime):
        return idx
    if isinstance(idx, datetime):
        return idx.date()
    to_date_fn = getattr(idx, "date", None)
    if callable(to_date_fn):
        try:
            result = to_date_fn()
        except (TypeError, ValueError):
            return None
        if isinstance(result, DateType):
            return result
    if isinstance(idx, str):
        try:
            return DateType.fromisoformat(idx[:10])
        except ValueError:
            return None
    return None


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _safe_ratio(v: Any) -> float | None:
    # Yahoo reports debt/equity as a percentage (e.g. 150.0 = 1.5). Convert to fraction.
    f = _safe_float(v)
    if f is None:
        return None
    return f / 100.0 if f > 5 else f
