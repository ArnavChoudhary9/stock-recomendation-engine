"""Walk-forward backtest with benchmark (NIFTY 50) comparison.

Loads OHLCV from the local SQLite DB, walks each symbol one ``step_days``
at a time, scores each window with the production scoring engine, and
measures the forward N-day return against the benchmark index.

Before running the backtest, make sure the benchmark is backfilled::

    python scripts/backfill.py --symbols ^NSEI --days 1825

Then::

    python scripts/backtest.py --preset nifty50
    python scripts/backtest.py --preset nifty50 --forward-days 60 --step-days 10
    python scripts/backtest.py --symbols RELIANCE,TCS,INFY --benchmark ^NSEI
    python scripts/backtest.py --preset nifty50 --verbose --top-n 20
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    CONFIG_DIR,
    IndicatorPeriods,
    ScoringConfig,
    ScoringWeights,
    SignalThresholds,
    load_data_config,
    load_processing_config,
    load_yaml,
)
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from tests.backtesting.harness import (
    DEFAULT_BENCHMARK,
    export_portfolio_csv,
    format_portfolio,
    format_report,
    run_backtest,
    simulate_portfolio,
)


def _load_config_file(path: Path) -> ScoringConfig:
    raw = load_yaml(path)
    return ScoringConfig(
        periods=IndicatorPeriods.model_validate(raw.get("features", {})),
        weights=ScoringWeights.model_validate(raw.get("scoring", {}).get("weights", {})),
        signals=SignalThresholds.model_validate(raw.get("signals", {})),
    )

log = logging.getLogger("backtest")

PRESETS_DIR = CONFIG_DIR / "symbols"


def _read_symbols_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"symbols file not found: {path}")
    syms = []
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


async def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward backtest vs. benchmark")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="Comma-separated symbols")
    src.add_argument("--symbols-file", help="Path to newline-delimited symbols file")
    src.add_argument(
        "--preset",
        choices=[p.stem for p in PRESETS_DIR.glob("*.txt")] or ["nifty50"],
        help="Named symbol list from config/symbols/",
    )
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK,
                        help="Yahoo index ticker, e.g. ^NSEI (NIFTY 50) or ^BSESN (SENSEX)")
    parser.add_argument("--forward-days", type=int, default=20)
    parser.add_argument("--step-days", type=int, default=20)
    parser.add_argument("--min-history-bars", type=int, default=220,
                        help="Minimum bars required before evaluation can start")
    parser.add_argument("--history-days", type=int, default=5 * 365,
                        help="Max calendar days of history to pull per symbol")
    parser.add_argument("--top-n", type=int, default=10,
                        help="Top-N for signal table; also portfolio size when --simulate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("--auto-fetch-benchmark", action="store_true",
                        help="If benchmark has no stored data, fetch it via Yahoo before running")
    parser.add_argument("--simulate", action="store_true",
                        help="Run the equal-weight top-N portfolio simulation vs the benchmark")
    parser.add_argument("--rebalance-days", type=int, default=20,
                        help="Minimum days between rebalances in --simulate mode")
    parser.add_argument("--transaction-cost-bps", type=float, default=0.0,
                        help="Per-side transaction cost in basis points (applied on turnover)")
    parser.add_argument("--export-csv", type=str, default=None,
                        help="Write the portfolio time-series to this CSV path (requires --simulate)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to an alternative processing.yaml to use for scoring")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    symbols = _resolve_symbols(args)
    log.info("backtest on %d symbols, benchmark=%s, forward=%dd, step=%dd",
             len(symbols), args.benchmark, args.forward_days, args.step_days)

    data_cfg = load_data_config()
    scoring_cfg = (
        _load_config_file(Path(args.config)) if args.config else load_processing_config()
    )
    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()
    try:
        if args.auto_fetch_benchmark:
            existing = await repo.get_latest_date(args.benchmark)
            if existing is None:
                log.info("no stored benchmark data — fetching %s from Yahoo", args.benchmark)
                provider = YahooFinanceProvider(
                    default_exchange=data_cfg.data.default_exchange,
                    min_interval_ms=data_cfg.data.rate_limit_delay_ms,
                )
                data_service = DataService(provider, repo, data_cfg)
                await data_service.refresh_symbol(args.benchmark)

        report = await run_backtest(
            repo, symbols, scoring_cfg,
            benchmark_symbol=args.benchmark,
            min_history_bars=args.min_history_bars,
            step_days=args.step_days,
            forward_days=args.forward_days,
            history_days=args.history_days,
        )
    finally:
        await repo.close()

    print(format_report(report, top_n_signals=args.top_n))

    if args.simulate:
        sim = simulate_portfolio(
            report.observations,
            top_n=args.top_n,
            rebalance_days=args.rebalance_days,
            transaction_cost_bps=args.transaction_cost_bps,
        )
        print(format_portfolio(sim))
        if args.export_csv:
            export_portfolio_csv(sim, Path(args.export_csv))
            log.info("portfolio time-series written to %s", args.export_csv)
    elif args.export_csv:
        log.warning("--export-csv ignored without --simulate")

    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
