"""Integration: data layer → processing → validated StockAnalysis output."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.config import DataConfig, DataProviderConfig, StorageConfig
from src.contracts import ScoringConfig
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.processing.service import DefaultProcessingService
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_end_to_end_analysis_produces_valid_output(tmp_path: Path) -> None:
    """A full backfill → compute_features → score → signals round-trip."""
    db_path = tmp_path / "proc.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        # Need >200 trading-days for SMA(200). Seed 300 calendar days so weekends drop ~210 bars.
        provider.seed_ohlcv("TCS", today - timedelta(days=400), days=400)
        provider.seed_fundamentals("TCS", pe=25.0, market_cap=1e12, roe=0.20)
        provider.seed_stock("TCS", name="Tata Consultancy", sector="IT")

        data_cfg = DataConfig(
            data=DataProviderConfig(provider="fake", backfill_days=400, rate_limit_delay_ms=0),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        data_service = DataService(provider, repo, data_cfg)
        await data_service.refresh_symbol("TCS")

        scoring_cfg = ScoringConfig()
        processor = DefaultProcessingService(data_service, scoring_cfg, lookback_days=400)
        analysis = await processor.analyze_stock("TCS")

        assert analysis.symbol == "TCS"
        assert 0.0 <= analysis.score <= 1.0
        # All sub-scores must be in unit range.
        for name in ("moving_average", "momentum", "volume", "volatility",
                     "fundamental", "support_resistance"):
            v = getattr(analysis.sub_scores, name)
            assert 0.0 <= v <= 1.0, f"{name}={v} out of range"

        # MovingAverages should be populated (no NaN in primary values).
        ma = analysis.moving_averages
        assert not math.isnan(ma.sma_200)
        assert not math.isnan(ma.sma_50)
        assert not math.isnan(ma.sma_20)

        # Signals dict must have every key the contract expects.
        for key in ("golden_cross", "death_cross", "ma_bullish_stack",
                    "ma_bearish_stack", "price_above_200sma", "price_below_200sma",
                    "overbought", "oversold", "momentum_strong", "volume_spike",
                    "near_52w_high", "near_52w_low"):
            assert key in analysis.signals

        # Metadata is deterministic — re-running with same config/data yields same hash.
        analysis2 = await processor.analyze_stock("TCS")
        assert analysis.metadata.config_hash == analysis2.metadata.config_hash
        assert analysis.score == analysis2.score
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_rank_stocks_sorts_descending(tmp_path: Path) -> None:
    db_path = tmp_path / "rank.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        for sym in ("AAA", "BBB", "CCC"):
            provider.seed_ohlcv(sym, today - timedelta(days=400), days=400)
            provider.seed_fundamentals(sym)
            provider.seed_stock(sym)

        data_cfg = DataConfig(
            data=DataProviderConfig(provider="fake", backfill_days=400, rate_limit_delay_ms=0),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        data_service = DataService(provider, repo, data_cfg)
        for sym in ("AAA", "BBB", "CCC"):
            await data_service.refresh_symbol(sym)

        processor = DefaultProcessingService(data_service, ScoringConfig(), lookback_days=400)
        ranked = await processor.rank_stocks(["AAA", "BBB", "CCC"])
        assert len(ranked) == 3
        scores = [a.score for a in ranked]
        assert scores == sorted(scores, reverse=True)
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_analyze_stock_raises_when_insufficient_data(tmp_path: Path) -> None:
    from src.processing.service import ProcessingError

    db_path = tmp_path / "short.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()
    try:
        today = datetime.now(UTC).date()
        provider = FakeProvider()
        provider.seed_ohlcv("SHORT", today - timedelta(days=30), days=30)
        provider.seed_stock("SHORT")

        data_cfg = DataConfig(
            data=DataProviderConfig(provider="fake", backfill_days=30, rate_limit_delay_ms=0),
            storage=StorageConfig(path=db_path, wal_mode=False),
        )
        data_service = DataService(provider, repo, data_cfg)
        await data_service.refresh_symbol("SHORT")

        processor = DefaultProcessingService(data_service, ScoringConfig(), lookback_days=30)
        with pytest.raises(ProcessingError):
            await processor.analyze_stock("SHORT")
    finally:
        await repo.close()
