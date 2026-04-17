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
from pathlib import Path

from src.contracts import OHLCVRow, ScoringConfig, ScoringWeights, SubScores
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


@dataclass(frozen=True)
class PrecomputedObservation:
    """Walk-forward evaluation with weight-independent inputs pre-baked.

    ``sub_scores`` and the forward/benchmark returns don't depend on
    :class:`ScoringWeights`, so a single pre-compute pass can feed many
    scoring trials via :func:`score_precomputed`.
    """

    symbol: str
    eval_date: date
    sub_scores: SubScores
    close_at_eval: float
    forward_return: float | None
    benchmark_return: float | None


def precompute_symbol(
    symbol: str,
    rows: list[OHLCVRow],
    config: ScoringConfig,
    benchmark: dict[date, float],
    *,
    min_history_bars: int,
    step_days: int,
    forward_days: int,
) -> list[PrecomputedObservation]:
    """Walk ``rows`` once and produce weight-independent observations.

    Periods and signals from ``config`` are consumed by ``compute_features``;
    ``config.weights`` is *not* used here — scoring happens later in
    :func:`score_precomputed`.
    """
    out: list[PrecomputedObservation] = []
    for i in range(min_history_bars, len(rows), step_days):
        window = rows[: i + 1]
        try:
            features = compute_features(symbol, window, None, config.periods, config.signals)
        except InsufficientDataError:
            continue
        sub = compute_sub_scores(features)
        fwd = _forward_return(rows, i, forward_days)
        bench = _benchmark_return(benchmark, rows[i].date, forward_days)
        out.append(
            PrecomputedObservation(
                symbol=symbol,
                eval_date=rows[i].date,
                sub_scores=sub,
                close_at_eval=rows[i].close,
                forward_return=fwd,
                benchmark_return=bench,
            )
        )
    return out


def score_precomputed(
    precomputed: list[PrecomputedObservation],
    weights: ScoringWeights,
) -> list[Observation]:
    """Apply ``weights`` to pre-computed sub-scores — the hot loop for optimizers."""
    out: list[Observation] = []
    for p in precomputed:
        alpha = (
            p.forward_return - p.benchmark_return
            if p.forward_return is not None and p.benchmark_return is not None
            else None
        )
        out.append(
            Observation(
                symbol=p.symbol,
                eval_date=p.eval_date,
                score=compose_score(p.sub_scores, weights),
                close_at_eval=p.close_at_eval,
                forward_return=p.forward_return,
                benchmark_return=p.benchmark_return,
                alpha=alpha,
            )
        )
    return out


async def precompute_all(
    repo: StockRepository,
    symbols: list[str],
    config: ScoringConfig,
    *,
    benchmark_symbol: str = DEFAULT_BENCHMARK,
    min_history_bars: int = 220,
    step_days: int = 20,
    forward_days: int = 20,
    history_days: int = 5 * 365,
) -> tuple[list[PrecomputedObservation], dict[str, int | str]]:
    """Run the expensive walk-forward once. Returns (pre-observations, params dict)."""
    end = date.today()
    start = end - timedelta(days=history_days)
    benchmark = await load_benchmark_series(repo, benchmark_symbol, days=history_days)
    if not benchmark:
        log.warning("no benchmark data for %s — alpha metrics will be None", benchmark_symbol)

    pre: list[PrecomputedObservation] = []
    for sym in symbols:
        rows = await repo.get_ohlcv(sym, start, end)
        if len(rows) < min_history_bars + forward_days:
            log.info("skipping %s (%d bars, need %d)",
                     sym, len(rows), min_history_bars + forward_days)
            continue
        obs = precompute_symbol(
            sym, rows, config, benchmark,
            min_history_bars=min_history_bars,
            step_days=step_days,
            forward_days=forward_days,
        )
        log.info("%s: %d precomputed observations", sym, len(obs))
        pre.extend(obs)

    params: dict[str, int | str] = {
        "benchmark": benchmark_symbol,
        "min_history_bars": min_history_bars,
        "step_days": step_days,
        "forward_days": forward_days,
        "history_days": history_days,
        "n_symbols": len(symbols),
    }
    return pre, params


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


# ---------------------------- Portfolio simulator ----------------------------


@dataclass(frozen=True)
class PortfolioStep:
    """One rebalance-period snapshot."""

    date: date
    picks: list[str]
    portfolio_return: float
    benchmark_return: float | None
    portfolio_value: float
    benchmark_value: float


@dataclass(frozen=True)
class PortfolioResult:
    """End-to-end portfolio simulation result."""

    steps: list[PortfolioStep]
    n_rebalances: int
    portfolio_cagr: float
    benchmark_cagr: float | None
    total_return: float
    benchmark_total_return: float | None
    alpha_cagr: float | None  # portfolio_cagr - benchmark_cagr
    sharpe: float | None
    max_drawdown: float
    avg_turnover: float  # mean fraction of portfolio replaced per rebalance


def _period_years(steps: list[PortfolioStep]) -> float:
    if len(steps) < 2:
        return 0.0
    days = (steps[-1].date - steps[0].date).days
    return max(days / 365.25, 1e-9)


def _cagr(final_value: float, start_value: float, years: float) -> float:
    if years <= 0 or start_value <= 0 or final_value <= 0:
        return 0.0
    return (final_value / start_value) ** (1.0 / years) - 1.0


def _max_drawdown(values: list[float]) -> float:
    """Largest peak-to-trough drop expressed as a negative fraction."""
    peak = values[0]
    worst = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = v / peak - 1.0 if peak > 0 else 0.0
        if dd < worst:
            worst = dd
    return worst


def _sharpe_like(period_returns: list[float], periods_per_year: float) -> float | None:
    """Annualised return/vol, no risk-free rate subtraction (personal-use proxy)."""
    if len(period_returns) < 2:
        return None
    mu = statistics.fmean(period_returns)
    sd = statistics.pstdev(period_returns)
    if sd == 0:
        return None
    return (mu / sd) * (periods_per_year ** 0.5)


def simulate_portfolio(
    observations: list[Observation],
    *,
    top_n: int,
    rebalance_days: int,
    transaction_cost_bps: float = 0.0,
) -> PortfolioResult:
    """Simulate an equal-weight top-N portfolio over the walk-forward observations.

    On each rebalance date (unique ``eval_date`` across observations), pick the
    ``top_n`` symbols with the highest scores *that also have a forward return*,
    equal-weight their forward returns, and compound the result. Benchmark uses
    the mean benchmark return of the same picks (they share one NIFTY window).

    ``transaction_cost_bps`` is applied symmetrically on turnover (e.g. 10 bps
    per side → 20 bps on fully replaced positions). 0 by default.
    """
    by_date: dict[date, list[Observation]] = {}
    for o in observations:
        if o.forward_return is None:
            continue
        by_date.setdefault(o.eval_date, []).append(o)

    sorted_dates = sorted(by_date)
    if not sorted_dates:
        return PortfolioResult(
            steps=[], n_rebalances=0, portfolio_cagr=0.0, benchmark_cagr=None,
            total_return=0.0, benchmark_total_return=None, alpha_cagr=None,
            sharpe=None, max_drawdown=0.0, avg_turnover=0.0,
        )

    # Throttle rebalances: keep dates separated by at least ``rebalance_days``.
    chosen: list[date] = [sorted_dates[0]]
    for d in sorted_dates[1:]:
        if (d - chosen[-1]).days >= rebalance_days:
            chosen.append(d)

    cost_per_side = transaction_cost_bps / 10_000.0
    port_value = 1.0
    bench_value = 1.0
    prev_picks: set[str] = set()
    steps: list[PortfolioStep] = []
    period_returns: list[float] = []
    turnovers: list[float] = []

    for d in chosen:
        bucket = sorted(by_date[d], key=lambda o: o.score, reverse=True)[:top_n]
        if not bucket:
            continue
        picks = [o.symbol for o in bucket]
        picks_set = set(picks)
        turnover = (
            len(picks_set.symmetric_difference(prev_picks)) / (2 * max(len(picks_set), 1))
            if prev_picks else 1.0
        )
        gross_ret = statistics.fmean(o.forward_return for o in bucket if o.forward_return is not None)
        net_ret = gross_ret - turnover * 2 * cost_per_side
        port_value *= 1.0 + net_ret

        bench_rets = [o.benchmark_return for o in bucket if o.benchmark_return is not None]
        bench_ret = statistics.fmean(bench_rets) if bench_rets else None
        if bench_ret is not None:
            bench_value *= 1.0 + bench_ret

        steps.append(PortfolioStep(
            date=d, picks=picks, portfolio_return=net_ret,
            benchmark_return=bench_ret,
            portfolio_value=port_value, benchmark_value=bench_value,
        ))
        period_returns.append(net_ret)
        turnovers.append(turnover)
        prev_picks = picks_set

    if not steps:
        return PortfolioResult(
            steps=[], n_rebalances=0, portfolio_cagr=0.0, benchmark_cagr=None,
            total_return=0.0, benchmark_total_return=None, alpha_cagr=None,
            sharpe=None, max_drawdown=0.0, avg_turnover=0.0,
        )

    years = _period_years(steps)
    periods_per_year = len(steps) / years if years > 0 else 0.0
    port_cagr = _cagr(steps[-1].portfolio_value, 1.0, years)

    # Benchmark CAGR from the compounded bench series (some periods may be None).
    bench_ret_series = [s.benchmark_return for s in steps if s.benchmark_return is not None]
    bench_cagr = (
        _cagr(steps[-1].benchmark_value, 1.0, years)
        if bench_ret_series else None
    )
    alpha_cagr = port_cagr - bench_cagr if bench_cagr is not None else None
    total_ret = steps[-1].portfolio_value - 1.0
    bench_total = steps[-1].benchmark_value - 1.0 if bench_ret_series else None

    return PortfolioResult(
        steps=steps,
        n_rebalances=len(steps),
        portfolio_cagr=port_cagr,
        benchmark_cagr=bench_cagr,
        total_return=total_ret,
        benchmark_total_return=bench_total,
        alpha_cagr=alpha_cagr,
        sharpe=_sharpe_like(period_returns, periods_per_year),
        max_drawdown=_max_drawdown([s.portfolio_value for s in steps]),
        avg_turnover=statistics.fmean(turnovers) if turnovers else 0.0,
    )


def format_portfolio(result: PortfolioResult) -> str:
    lines = ["-" * 70, "PORTFOLIO SIMULATION", "-" * 70]
    if result.n_rebalances == 0:
        lines.append("no observations with forward returns — nothing to simulate")
        return "\n".join(lines)
    lines.append(f"Rebalances:             {result.n_rebalances}")
    lines.append(f"Period:                 {result.steps[0].date} .. {result.steps[-1].date}")
    lines.append(f"Final portfolio value:  {result.steps[-1].portfolio_value:.4f}  ({_fmt_pct(result.total_return)})")
    if result.benchmark_total_return is not None:
        lines.append(f"Final benchmark value:  {result.steps[-1].benchmark_value:.4f}  ({_fmt_pct(result.benchmark_total_return)})")
    lines.append(f"Portfolio CAGR:         {_fmt_pct(result.portfolio_cagr)}")
    if result.benchmark_cagr is not None:
        lines.append(f"Benchmark CAGR:         {_fmt_pct(result.benchmark_cagr)}")
    if result.alpha_cagr is not None:
        lines.append(f"Alpha (CAGR diff):      {_fmt_pct(result.alpha_cagr)}")
    if result.sharpe is not None:
        lines.append(f"Sharpe-like:            {_fmt_float(result.sharpe)}")
    lines.append(f"Max drawdown:           {_fmt_pct(result.max_drawdown)}")
    lines.append(f"Avg turnover/rebalance: {_fmt_pct(result.avg_turnover)}")
    return "\n".join(lines)


def export_portfolio_csv(result: PortfolioResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["date,portfolio_value,benchmark_value,portfolio_return,benchmark_return,picks"]
    for s in result.steps:
        bench_ret = "" if s.benchmark_return is None else f"{s.benchmark_return:.6f}"
        picks = "|".join(s.picks)
        lines.append(
            f"{s.date.isoformat()},{s.portfolio_value:.6f},{s.benchmark_value:.6f},"
            f"{s.portfolio_return:.6f},{bench_ret},{picks}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
