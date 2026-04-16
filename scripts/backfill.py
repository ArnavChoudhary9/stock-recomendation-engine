"""Backfill historical OHLCV + fundamentals.

Symbol sources (pick one):
  --symbols RELIANCE,TCS,INFY          inline comma list
  --symbols-file path/to/list.txt      one symbol per line (# comments ok)
  --preset nifty50                     config/symbols/<name>.txt

Rate limiting: ``YahooFinanceProvider`` enforces a per-call minimum interval
(``rate_limit_delay_ms``) across every outbound request — history, info,
and search — so bulk runs can't burst past Yahoo's limits. Override with
``--delay-ms`` for large batches.

Examples::

    python scripts/backfill.py --preset nifty50
    python scripts/backfill.py --preset nifty50 --delay-ms 1500 --days 730
    python scripts/backfill.py --symbols-file my_watchlist.txt
    python scripts/backfill.py --symbols RELIANCE,TCS --days 90
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CONFIG_DIR, load_data_config
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService

log = logging.getLogger("backfill")

PRESETS_DIR = CONFIG_DIR / "symbols"


def _read_symbols_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"symbols file not found: {path}")
    symbols: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            symbols.append(line.upper())
    return symbols


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        return _read_symbols_file(Path(args.symbols_file))
    if args.preset:
        return _read_symbols_file(PRESETS_DIR / f"{args.preset}.txt")
    raise SystemExit("one of --symbols, --symbols-file, or --preset is required")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill historical market data")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="Comma-separated, e.g. RELIANCE,TCS,INFY")
    src.add_argument("--symbols-file", help="Path to a newline-delimited symbols file")
    src.add_argument(
        "--preset",
        choices=[p.stem for p in PRESETS_DIR.glob("*.txt")] or ["nifty50"],
        help="Named symbol list from config/symbols/",
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="History window (defaults to config.data.backfill_days)",
    )
    parser.add_argument(
        "--delay-ms", type=int, default=None,
        help="Milliseconds to sleep between symbols (default: config.data.rate_limit_delay_ms)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    symbols = _resolve_symbols(args)
    if not symbols:
        log.error("no symbols to backfill")
        return 2

    cfg = load_data_config()
    if args.days is not None:
        cfg = cfg.model_copy(update={"data": cfg.data.model_copy(update={"backfill_days": args.days})})
    if args.delay_ms is not None:
        cfg = cfg.model_copy(
            update={"data": cfg.data.model_copy(update={"rate_limit_delay_ms": args.delay_ms})}
        )

    # ~3 throttled Yahoo calls per symbol (search + ohlcv + fundamentals).
    est_seconds = len(symbols) * 3 * cfg.data.rate_limit_delay_ms / 1000.0
    log.info(
        "backfilling %d symbols (window=%dd, %dms between calls, ~%.0fs minimum)",
        len(symbols), cfg.data.backfill_days, cfg.data.rate_limit_delay_ms, est_seconds,
    )

    repo = SQLiteStockRepository(cfg.storage.path, wal_mode=cfg.storage.wal_mode)
    await repo.init()
    try:
        provider = YahooFinanceProvider(
            default_exchange=cfg.data.default_exchange,
            min_interval_ms=cfg.data.rate_limit_delay_ms,
        )
        service = DataService(provider, repo, cfg)
        results = await service.refresh_many(symbols)
    finally:
        await repo.close()

    ok = [s for s, n in results.items() if n > 0]
    empty = [s for s, n in results.items() if n == 0]
    total_bars = sum(results.values())
    log.info("done — %d symbols ok, %d empty/failed, %d total bars", len(ok), len(empty), total_bars)
    if empty:
        log.warning("no bars for: %s", ", ".join(empty))
    return 0 if ok else 1


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
