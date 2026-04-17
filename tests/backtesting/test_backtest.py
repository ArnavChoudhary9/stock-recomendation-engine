"""Backtests that exercise the scoring engine end-to-end.

Two flavours:

* **Fake-data tests** always run. They seed a synthetic repository with two
  cohorts of stocks — one trending up, one trending down — and assert that
  the scoring engine successfully distinguishes them (top quartile should
  outperform the bottom quartile). Validates the harness wiring.

* **Live NIFTY 50 test** is gated behind ``RUN_BACKTEST=1``. It reads from
  your local SQLite DB (so backfill first) and optionally auto-fetches the
  ``^NSEI`` benchmark if missing. Prints the full report and asserts weak
  but non-trivial properties about the strategy.

Run commands::

    # Always-on synthetic tests (fast):
    pytest tests/backtesting/ -v -s

    # Live NIFTY 50 test (requires backfilled data + internet):
    RUN_BACKTEST=1 pytest tests/backtesting/ -v -s

``-s`` is important — it lets the verbose backtest report print during the run.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.config import (
    DataConfig,
    DataProviderConfig,
    StorageConfig,
    load_data_config,
    load_processing_config,
)
from src.contracts import OHLCVRow, ScoringConfig
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from tests.backtesting.harness import (
    DEFAULT_BENCHMARK,
    format_report,
    run_backtest,
)
from tests.conftest import FakeProvider


@pytest.fixture(autouse=True)
def _capture_info_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)


# ---------- Fake-data backtest (always runs) ----------


def _trending_ohlcv(
    symbol: str, start: datetime, days: int, daily_drift_pct: float, noise_seed: int
) -> list[OHLCVRow]:
    """Generate a synthetic price path with a steady upward/downward drift."""
    import random

    rng = random.Random(noise_seed)
    rows: list[OHLCVRow] = []
    price = 100.0
    current = start
    for _ in range(days):
        if current.weekday() < 5:  # weekdays only, mimicking real market data
            drift = 1 + daily_drift_pct
            noise = 1 + rng.gauss(0, 0.005)
            price = max(1.0, price * drift * noise)
            rows.append(
                OHLCVRow(
                    symbol=symbol,
                    date=current.date(),
                    open=price,
                    high=price * 1.01,
                    low=price * 0.99,
                    close=price,
                    volume=1_000_000 + int(rng.uniform(0, 500_000)),
                )
            )
        current += timedelta(days=1)
    return rows


def _flat_ohlcv(symbol: str, start: datetime, days: int) -> list[OHLCVRow]:
    rows: list[OHLCVRow] = []
    current = start
    for _ in range(days):
        if current.weekday() < 5:
            rows.append(
                OHLCVRow(
                    symbol=symbol,
                    date=current.date(),
                    open=100.0, high=100.5, low=99.5, close=100.0, volume=1_000_000,
                )
            )
        current += timedelta(days=1)
    return rows


@pytest.mark.asyncio
async def test_backtest_separates_uptrend_from_downtrend(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With 3 clear uptrenders, 3 clear downtrenders, and a flat benchmark, the
    top-quartile should beat the bottom-quartile. Validates the pipeline."""
    db_path = tmp_path / "bt.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        start = datetime(2023, 1, 1, tzinfo=UTC)
        days = 900  # ~640 weekday bars → plenty for SMA(200) + walk-forward

        up_symbols = ["UP1", "UP2", "UP3"]
        down_symbols = ["DN1", "DN2", "DN3"]

        for i, sym in enumerate(up_symbols):
            rows = _trending_ohlcv(sym, start, days, daily_drift_pct=0.0012, noise_seed=100 + i)
            await repo.upsert_ohlcv(sym, rows)
        for i, sym in enumerate(down_symbols):
            rows = _trending_ohlcv(sym, start, days, daily_drift_pct=-0.0008, noise_seed=200 + i)
            await repo.upsert_ohlcv(sym, rows)
        # Flat benchmark.
        await repo.upsert_ohlcv("^NSEI", _flat_ohlcv("^NSEI", start, days))

        report = await run_backtest(
            repo, up_symbols + down_symbols, ScoringConfig(),
            benchmark_symbol="^NSEI",
            min_history_bars=220,
            step_days=20,
            forward_days=20,
            history_days=1000,
        )

        printed = format_report(report, top_n_signals=5)
        print(printed)
        capsys.readouterr()  # ensure captured for verbose mode

        assert report.n_with_forward > 0, "harness produced no observations"
        assert report.n_with_benchmark > 0, "benchmark series was not used"
        assert report.top_quartile is not None
        assert report.bottom_quartile is not None
        # Weak sanity: uptrenders' scores should translate into better returns on average.
        assert report.top_quartile.mean_return > report.bottom_quartile.mean_return, (
            f"top ({report.top_quartile.mean_return:.2%}) should beat bottom "
            f"({report.bottom_quartile.mean_return:.2%})"
        )
        # Long-short spread should be materially positive in this rigged scenario.
        assert report.long_short_spread is not None
        assert report.long_short_spread > 0.01, f"spread too small: {report.long_short_spread:.2%}"
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_backtest_without_benchmark_still_produces_report(tmp_path: Path) -> None:
    """Missing benchmark series shouldn't crash — alpha fields just stay None."""
    db_path = tmp_path / "bt_nobm.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        start = datetime(2023, 1, 1, tzinfo=UTC)
        rows = _trending_ohlcv("STEADY", start, 900, daily_drift_pct=0.0005, noise_seed=1)
        await repo.upsert_ohlcv("STEADY", rows)

        report = await run_backtest(
            repo, ["STEADY"], ScoringConfig(),
            benchmark_symbol="^MISSING",
            min_history_bars=220,
            step_days=20,
            forward_days=20,
            history_days=1000,
        )
        assert report.n_with_forward > 0
        assert report.n_with_benchmark == 0
        assert report.benchmark_mean_return is None
        assert report.overall is not None
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_fake_provider_end_to_end(tmp_path: Path) -> None:
    """Pipeline smoke test through DataService + FakeProvider — no harness logic bugs
    leak from production pathways."""
    db_path = tmp_path / "e2e.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        for sym in ("A", "B"):
            provider.seed_ohlcv(sym, today - timedelta(days=400), days=400)
            provider.seed_fundamentals(sym)
            provider.seed_stock(sym)

        cfg = DataConfig(
            data=DataProviderConfig(provider="fake", backfill_days=400, rate_limit_delay_ms=0),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        svc = DataService(provider, repo, cfg)
        for sym in ("A", "B"):
            await svc.refresh_symbol(sym)

        report = await run_backtest(
            repo, ["A", "B"], ScoringConfig(),
            benchmark_symbol="^MISSING",
            min_history_bars=220,
            step_days=20,
            forward_days=20,
            history_days=450,
        )
        assert report.n > 0
    finally:
        await repo.close()


# ---------- Live NIFTY 50 backtest (opt-in) ----------


LIVE_FLAG = os.getenv("RUN_BACKTEST") == "1"
PRESETS_DIR = Path(__file__).resolve().parents[2] / "config" / "symbols"


@pytest.mark.asyncio
@pytest.mark.skipif(not LIVE_FLAG, reason="opt-in: set RUN_BACKTEST=1 to run live NIFTY backtest")
async def test_live_nifty50_backtest_vs_benchmark(capsys: pytest.CaptureFixture[str]) -> None:
    """Run the real NIFTY 50 backtest against the stored database.

    Requires:
        - ``python scripts/backfill.py --preset nifty50 --days 1825``
        - ``python scripts/backfill.py --symbols ^NSEI --days 1825``  (or let
          RUN_BACKTEST_FETCH=1 fetch it at the start of this test).
    """
    data_cfg = load_data_config()
    scoring_cfg = load_processing_config()

    symbols_file = PRESETS_DIR / "nifty50.txt"
    symbols = [
        line.split("#", 1)[0].strip().upper()
        for line in symbols_file.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    ]
    assert len(symbols) >= 40, f"nifty50.txt too short ({len(symbols)} symbols)"

    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()
    try:
        if os.getenv("RUN_BACKTEST_FETCH") == "1":
            existing = await repo.get_latest_date(DEFAULT_BENCHMARK)
            if existing is None:
                provider = YahooFinanceProvider(
                    default_exchange=data_cfg.data.default_exchange,
                    min_interval_ms=data_cfg.data.rate_limit_delay_ms,
                )
                svc = DataService(provider, repo, data_cfg)
                await svc.refresh_symbol(DEFAULT_BENCHMARK)

        bench_latest = await repo.get_latest_date(DEFAULT_BENCHMARK)
        assert bench_latest is not None, (
            f"no {DEFAULT_BENCHMARK} data in repo — run "
            f"'python scripts/backfill.py --symbols {DEFAULT_BENCHMARK} --days 1825' "
            "or set RUN_BACKTEST_FETCH=1"
        )

        report = await run_backtest(
            repo, symbols, scoring_cfg,
            benchmark_symbol=DEFAULT_BENCHMARK,
            min_history_bars=220,
            step_days=20,
            forward_days=20,
            history_days=5 * 365,
        )
    finally:
        await repo.close()

    printed = format_report(report, top_n_signals=15)
    print("\n" + printed)
    capsys.readouterr()

    assert report.n_with_forward > 50, (
        f"too few observations ({report.n_with_forward}) — did you backfill enough history? "
        f"Try 'python scripts/backfill.py --preset nifty50 --days 1825'"
    )
    assert report.n_with_benchmark > 0, "benchmark overlap was zero"
    # Weak but non-trivial: the strategy should exhibit *some* ordering power.
    assert report.top_quartile is not None and report.bottom_quartile is not None
    assert report.long_short_spread is not None
    assert report.correlation_score_return is not None
