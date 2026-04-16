"""Initialise the SQLite database: apply migrations, enable WAL.

Usage::

    python scripts/setup_db.py
    python scripts/setup_db.py --db data/custom.db
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Make sure ``src`` is importable when this script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_data_config
from src.data.repositories.sqlite import SQLiteStockRepository


async def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the stocks SQLite database")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite file (defaults to config/data.yaml:storage.path)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cfg = load_data_config()
    db_path = args.db or cfg.storage.path
    repo = SQLiteStockRepository(db_path, wal_mode=cfg.storage.wal_mode)
    await repo.init()
    await repo.close()
    logging.info("initialised database at %s", db_path)
    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
