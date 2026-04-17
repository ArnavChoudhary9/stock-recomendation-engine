"""Run the full analysis pipeline: data layer → scoring → ranked output.

Reads OHLCV + fundamentals from the SQLite repo (no fresh fetches), computes
features, applies the scoring config from ``config/processing.yaml``, and
prints a ranked table plus per-stock signal breakdown.

Examples::

    python scripts/run_pipeline.py --symbols RELIANCE,TCS,INFY
    python scripts/run_pipeline.py --preset nifty50 --top 10
    python scripts/run_pipeline.py --preset nifty50 --format json > results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CONFIG_DIR, load_data_config, load_processing_config
from src.contracts import StockAnalysis
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.processing.service import DefaultProcessingService

log = logging.getLogger("pipeline")

PRESETS_DIR = CONFIG_DIR / "symbols"


def _read_symbols_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"symbols file not found: {path}")
    syms: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            syms.append(line.upper())
    return syms


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        return _read_symbols_file(Path(args.symbols_file))
    if args.preset:
        return _read_symbols_file(PRESETS_DIR / f"{args.preset}.txt")
    raise SystemExit("one of --symbols, --symbols-file, or --preset is required")


def _print_table(analyses: list[StockAnalysis], top: int | None) -> None:
    if top is not None:
        analyses = analyses[:top]
    if not analyses:
        print("(no analyses to display)")
        return

    header = f"{'Rank':>4}  {'Symbol':<12}  {'Score':>6}  {'Close':>10}  {'MA':>5}  {'Mom':>5}  {'Vol':>5}  Signals"
    print(header)
    print("-" * len(header))
    for i, a in enumerate(analyses, 1):
        active = [k for k, v in a.signals.items() if v is True][:4]
        print(
            f"{i:>4}  {a.symbol:<12}  {a.score:>6.3f}  {a.features.last_close:>10,.2f}  "
            f"{a.sub_scores.moving_average:>5.2f}  {a.sub_scores.momentum:>5.2f}  "
            f"{a.sub_scores.volume:>5.2f}  {','.join(active) or '-'}"
        )


def _print_json(analyses: list[StockAnalysis], top: int | None) -> None:
    if top is not None:
        analyses = analyses[:top]
    payload = [a.model_dump(mode="json") for a in analyses]
    json.dump(payload, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the scoring pipeline")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="Comma-separated symbols")
    src.add_argument("--symbols-file", help="Path to a newline-delimited symbols file")
    src.add_argument(
        "--preset",
        choices=[p.stem for p in PRESETS_DIR.glob("*.txt")] or ["nifty50"],
        help="Named symbol list from config/symbols/",
    )
    parser.add_argument("--top", type=int, default=None, help="Show only top N results")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument(
        "--lookback-days", type=int, default=400,
        help="Window of OHLCV to pull from the repo (must exceed SMA(200))",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    symbols = _resolve_symbols(args)

    data_cfg = load_data_config()
    scoring_cfg = load_processing_config()

    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()
    try:
        provider = YahooFinanceProvider(
            default_exchange=data_cfg.data.default_exchange,
            min_interval_ms=data_cfg.data.rate_limit_delay_ms,
        )
        data_service = DataService(provider, repo, data_cfg)
        processor = DefaultProcessingService(
            data_service, scoring_cfg, lookback_days=args.lookback_days
        )

        log.info("analysing %d symbols…", len(symbols))
        ranked = await processor.rank_stocks(symbols)
    finally:
        await repo.close()

    log.info("computed %d analyses (skipped %d)", len(ranked), len(symbols) - len(ranked))
    if args.format == "json":
        _print_json(ranked, args.top)
    else:
        _print_table(ranked, args.top)
    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
