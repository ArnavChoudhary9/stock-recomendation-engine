"""Random-search optimizer for scoring weights.

Samples weight vectors from a Dirichlet(alpha=1) distribution (uniform on the
6-simplex), evaluates each via the walk-forward backtest + portfolio simulator,
and tracks the best by the chosen objective (annualised alpha vs NIFTY by
default). The winner is written as a drop-in ``processing.yaml`` replacement,
and every trial is logged to CSV for later inspection.

Usage::

    python scripts/optimize_weights.py --preset nifty50 --trials 100 \
        --top-n 5 --rebalance-days 20 --forward-days 20 --history-days 1825 \
        --objective alpha_cagr --output config/processing.optimized.yaml \
        --log runs/trials.csv

Objectives:
    alpha_cagr          portfolio_cagr - benchmark_cagr  (default)
    raw_cagr            portfolio_cagr
    sharpe              Sharpe-like (annualised return/vol)
    long_short_spread   top-quartile minus bottom-quartile mean forward return
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    CONFIG_DIR,
    load_data_config,
    load_processing_config,
)
from src.contracts import ScoringConfig, ScoringWeights
from src.data.repositories.sqlite import SQLiteStockRepository
from tests.backtesting.harness import (
    DEFAULT_BENCHMARK,
    PortfolioResult,
    analyse,
    precompute_all,
    score_precomputed,
    simulate_portfolio,
)

log = logging.getLogger("optimize")

PRESETS_DIR = CONFIG_DIR / "symbols"

WEIGHT_FIELDS: tuple[str, ...] = (
    "moving_average",
    "momentum",
    "volume",
    "volatility",
    "fundamental",
    "support_resistance",
)


@dataclass
class TrialResult:
    trial: int
    weights: dict[str, float]
    portfolio_cagr: float
    benchmark_cagr: float | None
    alpha_cagr: float | None
    sharpe: float | None
    long_short_spread: float | None
    max_drawdown: float
    n_rebalances: int


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


def _sample_dirichlet(rng: random.Random, n: int, alpha: float = 1.0) -> list[float]:
    """Uniform sample on the n-simplex via normalized Gamma draws."""
    xs = [rng.gammavariate(alpha, 1.0) for _ in range(n)]
    s = sum(xs) or 1.0
    return [x / s for x in xs]


def _weights_from_sample(sample: list[float]) -> ScoringWeights:
    kwargs = dict(zip(WEIGHT_FIELDS, sample, strict=True))
    return ScoringWeights.model_validate(kwargs)


def _objective_value(
    name: str, sim: PortfolioResult, long_short_spread: float | None
) -> float | None:
    if name == "alpha_cagr":
        return sim.alpha_cagr
    if name == "raw_cagr":
        return sim.portfolio_cagr
    if name == "sharpe":
        return sim.sharpe
    if name == "long_short_spread":
        return long_short_spread
    raise ValueError(f"unknown objective: {name}")


def _weights_to_yaml(weights: ScoringWeights, base: ScoringConfig) -> str:
    """Serialize the full processing config with updated weights."""
    payload = {
        "features": base.periods.model_dump(),
        "scoring": {"weights": {f: getattr(weights, f) for f in WEIGHT_FIELDS}},
        "signals": base.signals.model_dump(),
    }
    return yaml.safe_dump(payload, sort_keys=False)


def _log_header() -> str:
    return (
        "trial,objective,portfolio_cagr,benchmark_cagr,alpha_cagr,sharpe,"
        "long_short_spread,max_drawdown,n_rebalances,"
        + ",".join(f"w_{f}" for f in WEIGHT_FIELDS)
    )


def _log_row(trial: TrialResult, objective: float | None) -> str:
    def f(v: float | None) -> str:
        return "" if v is None else f"{v:.6f}"
    weights = ",".join(f"{trial.weights[k]:.6f}" for k in WEIGHT_FIELDS)
    return (
        f"{trial.trial},{f(objective)},{f(trial.portfolio_cagr)},"
        f"{f(trial.benchmark_cagr)},{f(trial.alpha_cagr)},{f(trial.sharpe)},"
        f"{f(trial.long_short_spread)},{f(trial.max_drawdown)},"
        f"{trial.n_rebalances},{weights}"
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Random-search optimizer for scoring weights")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="Comma-separated symbols")
    src.add_argument("--symbols-file", help="Path to newline-delimited symbols file")
    src.add_argument(
        "--preset",
        choices=[p.stem for p in PRESETS_DIR.glob("*.txt")] or ["nifty50"],
        help="Named symbol list from config/symbols/",
    )
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--top-n", type=int, default=5, help="Portfolio size")
    parser.add_argument("--rebalance-days", type=int, default=20)
    parser.add_argument("--forward-days", type=int, default=20)
    parser.add_argument("--step-days", type=int, default=20)
    parser.add_argument("--min-history-bars", type=int, default=220)
    parser.add_argument("--history-days", type=int, default=5 * 365)
    parser.add_argument("--transaction-cost-bps", type=float, default=0.0)
    parser.add_argument(
        "--objective",
        choices=["alpha_cagr", "raw_cagr", "sharpe", "long_short_spread"],
        default="alpha_cagr",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument(
        "--output", type=str, default="config/processing.optimized.yaml",
        help="Where to write the winning processing.yaml",
    )
    parser.add_argument(
        "--log", type=str, default="runs/trials.csv",
        help="Where to write the per-trial CSV log",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    symbols = _resolve_symbols(args)
    log.info("optimizing over %d symbols, %d trials, objective=%s",
             len(symbols), args.trials, args.objective)

    data_cfg = load_data_config()
    base_cfg = load_processing_config()
    rng = random.Random(args.seed)

    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = [_log_header()]

    best_trial: TrialResult | None = None
    best_objective: float | None = None
    best_weights: ScoringWeights | None = None

    try:
        log.info("precomputing walk-forward observations (one-time expensive step)")
        precomputed, params = await precompute_all(
            repo, symbols, base_cfg,
            benchmark_symbol=args.benchmark,
            min_history_bars=args.min_history_bars,
            step_days=args.step_days,
            forward_days=args.forward_days,
            history_days=args.history_days,
        )
        log.info("precompute done: %d observations across %d symbols — trials will only rescore",
                 len(precomputed), len(symbols))

        for trial in range(1, args.trials + 1):
            sample = _sample_dirichlet(rng, len(WEIGHT_FIELDS))
            weights = _weights_from_sample(sample)
            observations = score_precomputed(precomputed, weights)
            report = analyse(observations, params=params)

            sim = simulate_portfolio(
                observations,
                top_n=args.top_n,
                rebalance_days=args.rebalance_days,
                transaction_cost_bps=args.transaction_cost_bps,
            )
            result = TrialResult(
                trial=trial,
                weights={k: getattr(weights, k) for k in WEIGHT_FIELDS},
                portfolio_cagr=sim.portfolio_cagr,
                benchmark_cagr=sim.benchmark_cagr,
                alpha_cagr=sim.alpha_cagr,
                sharpe=sim.sharpe,
                long_short_spread=report.long_short_spread,
                max_drawdown=sim.max_drawdown,
                n_rebalances=sim.n_rebalances,
            )
            obj = _objective_value(args.objective, sim, report.long_short_spread)
            log_lines.append(_log_row(result, obj))

            improved = obj is not None and (best_objective is None or obj > best_objective)
            marker = "  *new best*" if improved else ""
            log.info(
                "trial %3d/%d  obj=%s  cagr=%s  bench=%s  alpha=%s%s",
                trial, args.trials,
                f"{obj:+.4f}" if obj is not None else "n/a",
                f"{sim.portfolio_cagr:+.2%}",
                f"{sim.benchmark_cagr:+.2%}" if sim.benchmark_cagr is not None else "n/a",
                f"{sim.alpha_cagr:+.2%}" if sim.alpha_cagr is not None else "n/a",
                marker,
            )
            if improved:
                best_objective = obj
                best_trial = result
                best_weights = weights
    finally:
        await repo.close()
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        log.info("trial log written to %s", log_path)

    if best_weights is None or best_trial is None:
        log.error("no successful trials — nothing to write")
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_weights_to_yaml(best_weights, base_cfg), encoding="utf-8")

    print("=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"Trials run:        {args.trials}")
    print(f"Objective:         {args.objective}")
    print(f"Best value:        {best_objective:+.6f}")
    print(f"Best trial:        #{best_trial.trial}")
    print(f"Portfolio CAGR:    {best_trial.portfolio_cagr:+.2%}")
    if best_trial.benchmark_cagr is not None:
        print(f"Benchmark CAGR:    {best_trial.benchmark_cagr:+.2%}")
    if best_trial.alpha_cagr is not None:
        print(f"Alpha (CAGR):      {best_trial.alpha_cagr:+.2%}")
    if best_trial.sharpe is not None:
        print(f"Sharpe-like:       {best_trial.sharpe:+.3f}")
    print(f"Max drawdown:      {best_trial.max_drawdown:+.2%}")
    print("")
    print("Best weights:")
    for k in WEIGHT_FIELDS:
        print(f"  {k:<20} {best_trial.weights[k]:.4f}")
    print("")
    print(f"Weights written to: {out_path}")
    print(f"Trial log:          {log_path}")
    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
