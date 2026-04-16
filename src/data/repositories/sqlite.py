"""SQLite implementation of :class:`StockRepository`.

WAL mode is enabled for concurrent read performance. All writes run through
``asyncio.to_thread`` so the event loop stays unblocked. A single ``Connection``
is kept per repository instance (SQLite handles multi-thread access when
``check_same_thread=False``); mutations are serialized by an ``asyncio.Lock``.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import UTC, datetime
from datetime import date as DateType
from pathlib import Path

from src.contracts import Exchange, Fundamentals, OHLCVRow, StockInfo
from src.data.repositories.base import RepositoryError, StockRepository

log = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


class SQLiteStockRepository(StockRepository):
    """SQLite-backed repository. Call :meth:`init` once before use."""

    def __init__(self, db_path: Path | str, *, wal_mode: bool = True) -> None:
        self.db_path = Path(db_path)
        self.wal_mode = wal_mode
        self._conn: sqlite3.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def init(self) -> None:
        """Open connection, enable WAL, and apply migrations. Idempotent."""
        if self._conn is not None:
            return

        def _open() -> sqlite3.Connection:
            if self.db_path.parent and str(self.db_path) != ":memory:":
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                self.db_path, check_same_thread=False, isolation_level=None
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            if self.wal_mode and str(self.db_path) != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return conn

        self._conn = await asyncio.to_thread(_open)
        await self._apply_migrations()

    async def close(self) -> None:
        if self._conn is not None:
            conn = self._conn
            self._conn = None
            await asyncio.to_thread(conn.close)

    async def _apply_migrations(self) -> None:
        conn = self._require_conn()
        migrations = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        if not migrations:
            raise RepositoryError(f"No migrations found in {_MIGRATIONS_DIR}")

        def _run() -> None:
            for m in migrations:
                sql = m.read_text(encoding="utf-8")
                conn.executescript(sql)

        await asyncio.to_thread(_run)

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RepositoryError("Repository not initialised — call init() first")
        return self._conn

    async def get_ohlcv(
        self, symbol: str, start: DateType, end: DateType
    ) -> list[OHLCVRow]:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> list[OHLCVRow]:
            cur = conn.execute(
                """
                SELECT symbol, date, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND date BETWEEN ? AND ?
                ORDER BY date ASC
                """,
                (sym, start.isoformat(), end.isoformat()),
            )
            return [_row_to_ohlcv(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_q)

    async def get_latest_ohlcv(self, symbol: str) -> OHLCVRow | None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> OHLCVRow | None:
            cur = conn.execute(
                """
                SELECT symbol, date, open, high, low, close, volume
                FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1
                """,
                (sym,),
            )
            row = cur.fetchone()
            return _row_to_ohlcv(row) if row else None

        return await asyncio.to_thread(_q)

    async def get_latest_date(self, symbol: str) -> DateType | None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> DateType | None:
            cur = conn.execute(
                "SELECT MAX(date) AS d FROM ohlcv WHERE symbol = ?", (sym,)
            )
            row = cur.fetchone()
            if not row or row["d"] is None:
                return None
            return DateType.fromisoformat(row["d"])

        return await asyncio.to_thread(_q)

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> Fundamentals | None:
            cur = conn.execute(
                """
                SELECT symbol, date, pe, market_cap, roe, eps, debt_equity,
                       promoter_holding, dividend_yield
                FROM fundamentals WHERE symbol = ? ORDER BY date DESC LIMIT 1
                """,
                (sym,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Fundamentals(
                symbol=row["symbol"],
                date=DateType.fromisoformat(row["date"]),
                pe=row["pe"],
                market_cap=row["market_cap"],
                roe=row["roe"],
                eps=row["eps"],
                debt_equity=row["debt_equity"],
                promoter_holding=row["promoter_holding"],
                dividend_yield=row["dividend_yield"],
            )

        return await asyncio.to_thread(_q)

    async def upsert_ohlcv(self, symbol: str, rows: list[OHLCVRow]) -> int:
        if not rows:
            return 0
        conn = self._require_conn()
        sym = symbol.strip().upper()
        now = datetime.now(UTC).isoformat()
        payload = [
            (
                sym,
                r.date.isoformat(),
                r.open,
                r.high,
                r.low,
                r.close,
                r.volume,
            )
            for r in rows
        ]

        async with self._write_lock:
            def _w() -> int:
                # Ensure FK parent exists and bump updated_at for staleness tracking.
                conn.execute(
                    """
                    INSERT INTO stocks (symbol, name, exchange, updated_at)
                    VALUES (?, ?, 'NSE', ?)
                    ON CONFLICT(symbol) DO UPDATE SET updated_at = excluded.updated_at
                    """,
                    (sym, sym, now),
                )
                conn.executemany(
                    """
                    INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, date) DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume
                    """,
                    payload,
                )
                return len(payload)

            return await asyncio.to_thread(_w)

    async def upsert_fundamentals(self, symbol: str, data: Fundamentals) -> None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        async with self._write_lock:
            def _w() -> None:
                conn.execute(
                    """
                    INSERT INTO stocks (symbol, name, exchange, updated_at)
                    VALUES (?, ?, 'NSE', ?)
                    ON CONFLICT(symbol) DO NOTHING
                    """,
                    (sym, sym, datetime.now(UTC).isoformat()),
                )
                conn.execute(
                    """
                    INSERT INTO fundamentals (
                        symbol, date, pe, market_cap, roe, eps,
                        debt_equity, promoter_holding, dividend_yield
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, date) DO UPDATE SET
                        pe = excluded.pe,
                        market_cap = excluded.market_cap,
                        roe = excluded.roe,
                        eps = excluded.eps,
                        debt_equity = excluded.debt_equity,
                        promoter_holding = excluded.promoter_holding,
                        dividend_yield = excluded.dividend_yield
                    """,
                    (
                        sym,
                        data.date.isoformat(),
                        data.pe,
                        data.market_cap,
                        data.roe,
                        data.eps,
                        data.debt_equity,
                        data.promoter_holding,
                        data.dividend_yield,
                    ),
                )

            await asyncio.to_thread(_w)

    async def upsert_stock(self, info: StockInfo) -> None:
        conn = self._require_conn()
        sym = info.symbol.strip().upper()

        async with self._write_lock:
            def _w() -> None:
                conn.execute(
                    """
                    INSERT INTO stocks (symbol, name, sector, industry, exchange, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name = excluded.name,
                        sector = excluded.sector,
                        industry = excluded.industry,
                        exchange = excluded.exchange,
                        updated_at = excluded.updated_at
                    """,
                    (
                        sym,
                        info.name,
                        info.sector,
                        info.industry,
                        info.exchange,
                        info.updated_at.isoformat(),
                    ),
                )

            await asyncio.to_thread(_w)

    async def get_stock(self, symbol: str) -> StockInfo | None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> StockInfo | None:
            cur = conn.execute(
                "SELECT symbol, name, sector, industry, exchange, updated_at "
                "FROM stocks WHERE symbol = ?",
                (sym,),
            )
            row = cur.fetchone()
            return _row_to_stock_info(row) if row else None

        return await asyncio.to_thread(_q)

    async def list_symbols(self, sector: str | None = None) -> list[StockInfo]:
        conn = self._require_conn()

        def _q() -> list[StockInfo]:
            if sector is None:
                cur = conn.execute(
                    "SELECT symbol, name, sector, industry, exchange, updated_at "
                    "FROM stocks ORDER BY symbol ASC"
                )
            else:
                cur = conn.execute(
                    "SELECT symbol, name, sector, industry, exchange, updated_at "
                    "FROM stocks WHERE sector = ? ORDER BY symbol ASC",
                    (sector,),
                )
            return [_row_to_stock_info(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_q)

    async def touch_symbol(self, symbol: str) -> None:
        conn = self._require_conn()
        sym = symbol.strip().upper()
        now = datetime.now(UTC).isoformat()
        async with self._write_lock:
            def _w() -> None:
                conn.execute(
                    """
                    INSERT INTO stocks (symbol, name, exchange, updated_at)
                    VALUES (?, ?, 'NSE', ?)
                    ON CONFLICT(symbol) DO UPDATE SET updated_at = excluded.updated_at
                    """,
                    (sym, sym, now),
                )

            await asyncio.to_thread(_w)

    async def last_updated(self, symbol: str) -> datetime | None:
        conn = self._require_conn()
        sym = symbol.strip().upper()

        def _q() -> datetime | None:
            cur = conn.execute(
                "SELECT updated_at FROM stocks WHERE symbol = ?", (sym,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return datetime.fromisoformat(row["updated_at"])

        return await asyncio.to_thread(_q)


def _row_to_ohlcv(row: sqlite3.Row) -> OHLCVRow:
    return OHLCVRow(
        symbol=row["symbol"],
        date=DateType.fromisoformat(row["date"]),
        open=row["open"],
        high=row["high"],
        low=row["low"],
        close=row["close"],
        volume=row["volume"],
    )


def _row_to_stock_info(row: sqlite3.Row) -> StockInfo:
    exchange: Exchange = row["exchange"] if row["exchange"] in ("NSE", "BSE") else "NSE"
    return StockInfo(
        symbol=row["symbol"],
        name=row["name"],
        sector=row["sector"],
        industry=row["industry"],
        exchange=exchange,
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
