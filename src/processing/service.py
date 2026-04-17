"""ProcessingService — deterministic analysis pipeline.

The service is stateless and synchronous end-to-end for a single stock; batch
ranking ``rank_stocks`` fans out with ``asyncio.gather`` over the data fetcher.
All cross-module dependencies come in through a minimal ``DataSource`` protocol
so ``src.processing`` has no import dependency on ``src.data``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from src.contracts import (
    AnalysisMetadata,
    Features,
    Fundamentals,
    OHLCVRow,
    ScoringConfig,
    StockAnalysis,
    StockInfo,
)
from src.processing.features import InsufficientDataError, compute_features
from src.processing.scoring import (
    SCORING_VERSION,
    compose_score,
    compute_sub_scores,
    derive_recommendation,
)
from src.processing.signals import generate_signals

log = logging.getLogger(__name__)


class DataSource(Protocol):
    """Minimal protocol covering what processing needs from the data layer."""

    async def get_ohlcv(
        self, symbol: str, start: date, end: date, *, refresh: bool = False
    ) -> list[OHLCVRow]: ...

    async def get_fundamentals(
        self, symbol: str, *, refresh: bool = False
    ) -> Fundamentals | None: ...

    async def ensure_stock(self, symbol: str) -> StockInfo | None: ...


class ProcessingError(Exception):
    """Base exception for processing-layer failures."""


class ProcessingService(ABC):
    """Abstract processing service — see :class:`DefaultProcessingService` for impl."""

    @abstractmethod
    async def analyze_stock(self, symbol: str) -> StockAnalysis: ...

    @abstractmethod
    async def rank_stocks(self, symbols: list[str]) -> list[StockAnalysis]: ...

    @abstractmethod
    def compute_features(
        self,
        symbol: str,
        ohlcv: list[OHLCVRow],
        fundamentals: Fundamentals | None,
    ) -> Features: ...

    @abstractmethod
    def compute_score(self, features: Features) -> float: ...

    @abstractmethod
    def generate_signals(self, features: Features) -> dict[str, bool | str]: ...


class DefaultProcessingService(ProcessingService):
    """Concrete processing service backed by the indicator + scoring modules."""

    def __init__(
        self,
        data_source: DataSource,
        config: ScoringConfig,
        *,
        lookback_days: int = 400,
    ) -> None:
        self.data = data_source
        self.config = config
        self.lookback_days = lookback_days
        self._config_hash = _hash_config(config)

    def compute_features(
        self,
        symbol: str,
        ohlcv: list[OHLCVRow],
        fundamentals: Fundamentals | None,
    ) -> Features:
        return compute_features(
            symbol,
            ohlcv,
            fundamentals,
            self.config.periods,
            self.config.signals,
        )

    def compute_score(self, features: Features) -> float:
        sub = compute_sub_scores(features)
        return compose_score(sub, self.config.weights)

    def generate_signals(self, features: Features) -> dict[str, bool | str]:
        return generate_signals(features, self.config.signals)

    async def analyze_stock(self, symbol: str) -> StockAnalysis:
        end = datetime.now(UTC).date()
        start = end - timedelta(days=self.lookback_days)
        ohlcv = await self.data.get_ohlcv(symbol, start, end)
        if not ohlcv:
            raise ProcessingError(f"No OHLCV data for {symbol}")
        fundamentals = await self.data.get_fundamentals(symbol)
        try:
            features = self.compute_features(symbol, ohlcv, fundamentals)
        except InsufficientDataError as e:
            raise ProcessingError(f"Insufficient data for {symbol}: {e}") from e

        sub_scores = compute_sub_scores(features)
        score = compose_score(sub_scores, self.config.weights)
        signals = generate_signals(features, self.config.signals)
        recommendation, rationale = derive_recommendation(
            score, sub_scores, features.fundamentals, signals
        )

        return StockAnalysis(
            symbol=symbol,
            timestamp=features.as_of,
            moving_averages=features.moving_averages,
            features=features,
            score=score,
            sub_scores=sub_scores,
            signals=signals,
            metadata=AnalysisMetadata(
                config_hash=self._config_hash,
                scoring_version=SCORING_VERSION,
                computed_at=features.as_of,
                data_points_used=len(ohlcv),
                warnings=[],
            ),
            recommendation=recommendation,
            recommendation_rationale=rationale,
        )

    async def rank_stocks(self, symbols: list[str]) -> list[StockAnalysis]:
        analyses: list[StockAnalysis] = []
        for sym in symbols:
            try:
                analyses.append(await self.analyze_stock(sym))
            except ProcessingError as e:
                log.warning("skipping %s: %s", sym, e)
        analyses.sort(key=lambda a: a.score, reverse=True)
        return analyses


def _hash_config(config: ScoringConfig) -> str:
    """Stable fingerprint of the scoring config for reproducibility metadata."""
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
