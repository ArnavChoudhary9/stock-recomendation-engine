"""Backfill historical OHLCV + fundamentals for one or more symbols.

Usage::

    python scripts/backfill.py --symbols RELIANCE,TCS,INFY
    python scripts/backfill.py --symbols RELIANCE --days 730
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_data_config
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService


async def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill historical market data")
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list, e.g. RELIANCE,TCS,INFY",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Days of history to fetch (defaults to config.data.backfill_days)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        logging.error("no symbols provided")
        return 2

    cfg = load_data_config()
    days = args.days or cfg.data.backfill_days
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days)

    repo = SQLiteStockRepository(cfg.storage.path, wal_mode=cfg.storage.wal_mode)
    await repo.init()
    try:
        provider = YahooFinanceProvider(default_exchange=cfg.data.default_exchange)
        service = DataService(provider, repo, cfg)

        total = 0
        for sym in symbols:
            await service.ensure_stock(sym)
            rows = await service.get_ohlcv(sym, start, end, refresh=True)
            await service.get_fundamentals(sym, refresh=True)
            logging.info("%s: %d bars stored (window %s..%s)", sym, len(rows), start, end)
            total += len(rows)
        logging.info("backfill complete — %d total bars across %d symbols", total, len(symbols))
    finally:
        await repo.close()
    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
