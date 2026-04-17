"""Backtesting harness — walk-forward scoring vs. benchmark.

The harness takes a set of symbols and, for each evaluation date, computes a
score using only data available up to that point, then measures the forward
N-day return. A benchmark series (e.g. NIFTY 50, ``^NSEI``) lets us compute
*alpha* — per-signal return minus benchmark return over the same window.

This module is pure library code. CLI runner lives in ``scripts/backtest.py``.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta

from src.contracts import OHLCVRow, ScoringConfig
from src.data.repositories.base import StockRepository
from src.processing.features import InsufficientDataError, compute_features
from src.processing.scoring import compose_score, compute_sub_scores

log = logging.getLogger(__name__)

DEFAULT_BENCHMARK = "^NSEI"  # NIFTY 50 on Yahoo Finance


@dataclass(frozen=True)
class Observation:
    """One (symbol, eval_date) evaluation produced by the walk-forward loop."""

    symbol: str
    eval_date: date
    score: float
    close_at_eval: float
    forward_return: float | None
    benchmark_return: float | None
    alpha: float | None  # forward_return - benchmark_return; None if either missing


@dataclass(frozen=True)
class QuartileStats:
    """Aggregate stats for one score quartile."""

    mean_return: float
    median_return: float
    win_rate: float  # fraction with forward_return > 0
    beat_benchmark_rate: float  # fraction with alpha > 0
    mean_alpha: float
    std_return: float
    count: int


@dataclass(frozen=True)
class BacktestReport:
    observations: list[Observation]
    n: int
    n_with_forward: int
    n_with_benchmark: int
    correlation_score_return: float | None
    correlation_score_alpha: float | None
    top_quartile: QuartileStats | None
    bottom_quartile: QuartileStats | None
    overall: QuartileStats | None
    benchmark_mean_return: float | None
    long_short_spread: float | None  # top_q mean - bot_q mean
    sharpe_like_top: float | None
    params: dict[str, int | str] = field(default_factory=dict)


def _forward_return(rows: list[OHLCVRow], eval_idx: int, forward_days: int) -> float | None:
    target = eval_idx + forward_days
    if target >= len(rows) or rows[eval_idx].close == 0:
        return None
    return rows[target].close / rows[eval_idx].close - 1.0


def _benchmark_return(
    benchmark: dict[date, float], eval_date: date, forward_days: int
) -> float | None:
    """Return ``close_{t+N} / close_t - 1`` using the nearest available trading days.

    The benchmark series uses its own trading calendar, which may not align
    perfectly with individual stocks on holidays. We snap to the first
    benchmark date ``>= eval_date`` for the start, and ``>= eval_date + N``
    for the end.
    """
    if not benchmark:
        return None
    dates = sorted(benchmark)
    start = _first_date_gte(dates, eval_date)
    if start is None:
        return None
    target = start + timedelta(days=forward_days)
    end = _first_date_gte(dates, target)
    if end is None:
        return None
    p0 = benchmark[start]
    p1 = benchmark[end]
    if p0 == 0:
        return None
    return p1 / p0 - 1.0


def _first_date_gte(sorted_dates: list[date], target: date) -> date | None:
    for d in sorted_dates:
        if d >= target:
            return d
    return None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    try:
        return statistics.correlation(xs, ys)
    except (statistics.StatisticsError, ValueError):
        return None


def _quartile_stats(obs: list[Observation]) -> QuartileStats | None:
    scored = [o for o in obs if o.forward_return is not None]
    if not scored:
        return None
    rets = [o.forward_return for o in scored if o.forward_return is not None]
    alphas = [o.alpha for o in scored if o.alpha is not None]
    wins = sum(1 for r in rets if r > 0)
    beats = sum(1 for a in alphas if a > 0)
    return QuartileStats(
        mean_return=statistics.fmean(rets),
        median_return=statistics.median(rets),
        win_rate=wins / len(rets),
        beat_benchmark_rate=beats / len(alphas) if alphas else 0.0,
        mean_alpha=statistics.fmean(alphas) if alphas else 0.0,
        std_return=statistics.pstdev(rets) if len(rets) > 1 else 0.0,
        count=len(scored),
    )


def evaluate_symbol(
    symbol: str,
    rows: list[OHLCVRow],
    config: ScoringConfig,
    benchmark: dict[date, float],
    *,
    min_history_bars: int,
    step_days: int,
    forward_days: int,
) -> list[Observation]:
    """Produce an :class:`Observation` every ``step_days`` bars in ``rows``."""
    out: list[Observation] = []
    for i in range(min_history_bars, len(rows), step_days):
        window = rows[: i + 1]
        try:
            features = compute_features(symbol, window, None, config.periods, config.signals)
        except InsufficientDataError:
            continue
        sub = compute_sub_scores(features)
        score = compose_score(sub, config.weights)
        fwd = _forward_return(rows, i, forward_days)
        bench = _benchmark_return(benchmark, rows[i].date, forward_days)
        alpha = fwd - bench if (fwd is not None and bench is not None) else None
        out.append(
            Observation(
                symbol=symbol,
                eval_date=rows[i].date,
                score=score,
                close_at_eval=rows[i].close,
                forward_return=fwd,
                benchmark_return=bench,
                alpha=alpha,
            )
        )
    return out


def analyse(observations: list[Observation], *, params: dict[str, int | str]) -> BacktestReport:
    """Summarise observations into per-quartile stats and overall metrics."""
    scored = sorted(
        (o for o in observations if o.forward_return is not None),
        key=lambda o: o.score,
    )
    n = len(observations)
    n_fwd = len(scored)
    n_bench = sum(1 for o in scored if o.benchmark_return is not None)

    if not scored:
        return BacktestReport(
            observations=observations, n=n, n_with_forward=0, n_with_benchmark=0,
            correlation_score_return=None, correlation_score_alpha=None,
            top_quartile=None, bottom_quartile=None, overall=None,
            benchmark_mean_return=None, long_short_spread=None, sharpe_like_top=None,
            params=params,
        )

    q = max(1, n_fwd // 4)
    top = scored[-q:]
    bottom = scored[:q]
    top_stats = _quartile_stats(top)
    bot_stats = _quartile_stats(bottom)
    all_stats = _quartile_stats(scored)

    xs_score = [o.score for o in scored]
    ys_return = [o.forward_return or 0.0 for o in scored]
    alpha_obs = [o for o in scored if o.alpha is not None]
    corr_return = _pearson(xs_score, ys_return)
    corr_alpha = _pearson(
        [o.score for o in alpha_obs],
        [o.alpha or 0.0 for o in alpha_obs],
    )

    bench_mean = (
        statistics.fmean(o.benchmark_return for o in scored if o.benchmark_return is not None)
        if n_bench else None
    )
    long_short = (
        top_stats.mean_return - bot_stats.mean_return
        if top_stats and bot_stats else None
    )
    sharpe_top = (
        top_stats.mean_return / top_stats.std_return
        if top_stats and top_stats.std_return > 0 else None
    )

    return BacktestReport(
        observations=observations,
        n=n,
        n_with_forward=n_fwd,
        n_with_benchmark=n_bench,
        correlation_score_return=corr_return,
        correlation_score_alpha=corr_alpha,
        top_quartile=top_stats,
        bottom_quartile=bot_stats,
        overall=all_stats,
        benchmark_mean_return=bench_mean,
        long_short_spread=long_short,
        sharpe_like_top=sharpe_top,
        params=params,
    )


async def load_benchmark_series(
    repo: StockRepository, symbol: str, *, days: int
) -> dict[date, float]:
    """Load closes-by-date for a benchmark ticker from the repo."""
    end = date.today()
    start = end - timedelta(days=days)
    rows = await repo.get_ohlcv(symbol, start, end)
    return {r.date: r.close for r in rows}


async def run_backtest(
    repo: StockRepository,
    symbols: list[str],
    config: ScoringConfig,
    *,
    benchmark_symbol: str = DEFAULT_BENCHMARK,
    min_history_bars: int = 220,
    step_days: int = 20,
    forward_days: int = 20,
    history_days: int = 5 * 365,
) -> BacktestReport:
    """Top-level entry: pulls history, walks each symbol, produces a report."""
    end = date.today()
    start = end - timedelta(days=history_days)
    benchmark = await load_benchmark_series(repo, benchmark_symbol, days=history_days)
    if not benchmark:
        log.warning("no benchmark data for %s — alpha metrics will be None", benchmark_symbol)

    all_obs: list[Observation] = []
    for sym in symbols:
        rows = await repo.get_ohlcv(sym, start, end)
        if len(rows) < min_history_bars + forward_days:
            log.info("skipping %s (%d bars, need %d)",
                     sym, len(rows), min_history_bars + forward_days)
            continue
        obs = evaluate_symbol(
            sym, rows, config, benchmark,
            min_history_bars=min_history_bars,
            step_days=step_days,
            forward_days=forward_days,
        )
        log.info("%s: %d observations", sym, len(obs))
        all_obs.extend(obs)

    params: dict[str, int | str] = {
        "benchmark": benchmark_symbol,
        "min_history_bars": min_history_bars,
        "step_days": step_days,
        "forward_days": forward_days,
        "history_days": history_days,
        "n_symbols": len(symbols),
    }
    return analyse(all_obs, params=params)


# ----------------------------- Pretty printing -----------------------------


def _fmt_pct(x: float | None, width: int = 7) -> str:
    if x is None:
        return f"{'n/a':>{width}}"
    return f"{x:>+{width - 1}.2%}"


def _fmt_float(x: float | None, width: int = 7, decimals: int = 3) -> str:
    if x is None:
        return f"{'n/a':>{width}}"
    return f"{x:>+{width - 1}.{decimals}f}"


def format_report(report: BacktestReport, *, top_n_signals: int = 10) -> str:
    """Render a verbose text report for the CLI / pytest output."""
    lines: list[str] = []
    p = report.params
    lines.append("=" * 70)
    lines.append("BACKTEST REPORT")
    lines.append("=" * 70)
    lines.append(f"Symbols:             {p.get('n_symbols')}")
    lines.append(f"Benchmark:           {p.get('benchmark')}")
    lines.append(f"Forward window:      {p.get('forward_days')} trading days")
    lines.append(f"Step between evals:  {p.get('step_days')} bars")
    lines.append(f"Min history bars:    {p.get('min_history_bars')}")
    lines.append(f"History window:      {p.get('history_days')} days")
    lines.append("")
    lines.append(f"Observations:                {report.n}")
    lines.append(f"  with forward return:       {report.n_with_forward}")
    lines.append(f"  with benchmark alpha:      {report.n_with_benchmark}")
    lines.append("")

    if report.benchmark_mean_return is not None:
        lines.append(f"Benchmark mean fwd return:   {_fmt_pct(report.benchmark_mean_return)}")
    if report.overall:
        lines.append(f"Overall mean fwd return:     {_fmt_pct(report.overall.mean_return)}")
        lines.append(f"Overall win rate:            {_fmt_pct(report.overall.win_rate)}")
    if report.correlation_score_return is not None:
        lines.append(f"Corr(score, fwd return):     {_fmt_float(report.correlation_score_return)}")
    if report.correlation_score_alpha is not None:
        lines.append(f"Corr(score, alpha):          {_fmt_float(report.correlation_score_alpha)}")
    if report.long_short_spread is not None:
        lines.append(f"Top-q minus bot-q spread:    {_fmt_pct(report.long_short_spread)}")
    if report.sharpe_like_top is not None:
        lines.append(f"Top-q return/stddev:         {_fmt_float(report.sharpe_like_top)}")
    lines.append("")

    lines.append("-" * 70)
    lines.append("QUARTILE BREAKDOWN")
    lines.append("-" * 70)
    lines.append(
        f"{'bucket':<10}  {'n':>4}  {'mean ret':>9}  {'median':>8}  "
        f"{'win':>6}  {'beat_bm':>7}  {'alpha':>7}  {'std':>7}"
    )
    for name, stats in (
        ("top 25%", report.top_quartile),
        ("all", report.overall),
        ("bottom 25%", report.bottom_quartile),
    ):
        if stats is None:
            continue
        lines.append(
            f"{name:<10}  {stats.count:>4}  {_fmt_pct(stats.mean_return)}  "
            f"{_fmt_pct(stats.median_return, 8)}  {_fmt_pct(stats.win_rate, 6)}  "
            f"{_fmt_pct(stats.beat_benchmark_rate, 7)}  {_fmt_pct(stats.mean_alpha)}  "
            f"{stats.std_return:>7.2%}"
        )
    lines.append("")

    scored = [o for o in report.observations if o.forward_return is not None]
    scored.sort(key=lambda o: o.score, reverse=True)

    if scored and top_n_signals > 0:
        lines.append("-" * 70)
        lines.append(f"TOP {top_n_signals} SIGNALS BY SCORE")
        lines.append("-" * 70)
        lines.append(
            f"{'symbol':<10}  {'date':<12}  {'score':>6}  {'fwd':>7}  {'bench':>7}  {'alpha':>7}"
        )
        for o in scored[:top_n_signals]:
            lines.append(_fmt_obs_row(o))
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"BOTTOM {top_n_signals} SIGNALS BY SCORE")
        lines.append("-" * 70)
        lines.append(
            f"{'symbol':<10}  {'date':<12}  {'score':>6}  {'fwd':>7}  {'bench':>7}  {'alpha':>7}"
        )
        for o in scored[-top_n_signals:]:
            lines.append(_fmt_obs_row(o))
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def _fmt_obs_row(o: Observation) -> str:
    return (
        f"{o.symbol:<10}  {o.eval_date.isoformat():<12}  {o.score:>6.3f}  "
        f"{_fmt_pct(o.forward_return)}  {_fmt_pct(o.benchmark_return)}  {_fmt_pct(o.alpha)}"
    )
