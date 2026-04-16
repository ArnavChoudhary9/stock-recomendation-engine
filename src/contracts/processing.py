"""Processing layer contracts: indicators, features, scoring, signals, analysis output."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Alignment = Literal["bullish", "bearish", "mixed"]
Slope = Literal["rising", "falling", "flat"]
Crossover = Literal["golden_cross", "death_cross"]
MarketCapTier = Literal["large", "mid", "small", "micro"]


class MovingAverages(BaseModel):
    """Moving-average state for a stock — first-class signal in this system."""

    model_config = ConfigDict(frozen=True)

    sma_20: float
    sma_50: float
    sma_200: float
    ema_12: float
    ema_26: float
    price_to_sma20_pct: float = Field(..., description="Signed % distance of price from SMA(20)")
    price_to_sma50_pct: float
    price_to_sma200_pct: float
    alignment: Alignment
    sma50_slope: Slope
    sma200_slope: Slope
    crossover: Crossover | None = None
    crossover_days_ago: int | None = Field(None, ge=0)


class Momentum(BaseModel):
    model_config = ConfigDict(frozen=True)

    rsi_14: float = Field(..., ge=0, le=100)
    return_5d: float
    return_10d: float
    return_20d: float


class VolumeFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_volume: int = Field(..., ge=0)
    avg_volume_20d: float = Field(..., ge=0)
    volume_ratio: float = Field(..., ge=0, description="current / 20d average")
    obv: float


class Volatility(BaseModel):
    model_config = ConfigDict(frozen=True)

    atr_14: float = Field(..., ge=0)
    std_dev_20: float = Field(..., ge=0)


class FundamentalFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)

    pe: float | None = None
    pe_vs_sector_median: float | None = Field(
        None, description="(pe - sector_median) / sector_median; negative = cheaper than sector"
    )
    market_cap: float | None = Field(None, ge=0)
    market_cap_tier: MarketCapTier | None = None
    roe: float | None = None
    roe_sector_rank: float | None = Field(None, ge=0, le=1, description="Percentile within sector")


class SupportResistance(BaseModel):
    model_config = ConfigDict(frozen=True)

    high_52w: float = Field(..., gt=0)
    low_52w: float = Field(..., gt=0)
    distance_to_52w_high_pct: float = Field(..., description="Signed %; negative = below high")
    distance_to_52w_low_pct: float
    near_52w_high: bool
    near_52w_low: bool


class Features(BaseModel):
    """Bundle of all computed features for a stock at one point in time."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    as_of: datetime
    last_close: float = Field(..., gt=0)
    moving_averages: MovingAverages
    momentum: Momentum
    volume: VolumeFeatures
    volatility: Volatility
    fundamentals: FundamentalFeatures
    support_resistance: SupportResistance

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class ScoringWeights(BaseModel):
    """Weights for the composite score. Must sum to 1.0 (validated)."""

    moving_average: float = Field(0.25, ge=0, le=1)
    momentum: float = Field(0.20, ge=0, le=1)
    volume: float = Field(0.15, ge=0, le=1)
    volatility: float = Field(0.10, ge=0, le=1)
    fundamental: float = Field(0.20, ge=0, le=1)
    support_resistance: float = Field(0.10, ge=0, le=1)

    def total(self) -> float:
        return (
            self.moving_average
            + self.momentum
            + self.volume
            + self.volatility
            + self.fundamental
            + self.support_resistance
        )


class SignalThresholds(BaseModel):
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    volume_spike_multiplier: float = 2.0
    near_high_low_pct: float = 0.05
    crossover_lookback_days: int = 5
    ma_slope_period: int = 10
    ma_slope_flat_threshold: float = 0.005


class IndicatorPeriods(BaseModel):
    sma_periods: list[int] = Field(default_factory=lambda: [20, 50, 200])
    ema_periods: list[int] = Field(default_factory=lambda: [12, 26])
    rsi_period: int = 14
    atr_period: int = 14
    volatility_period: int = 20
    momentum_periods: list[int] = Field(default_factory=lambda: [5, 10, 20])
    volume_avg_period: int = 20


class ScoringConfig(BaseModel):
    """Full scoring configuration — snapshot stored in AnalysisMetadata for reproducibility."""

    weights: ScoringWeights = Field(default_factory=lambda: ScoringWeights.model_validate({}))
    signals: SignalThresholds = Field(
        default_factory=lambda: SignalThresholds.model_validate({})
    )
    periods: IndicatorPeriods = Field(default_factory=lambda: IndicatorPeriods.model_validate({}))


class SubScores(BaseModel):
    """Individual sub-scores in [0, 1] before weighting — useful for debugging and UI breakdown."""

    model_config = ConfigDict(frozen=True)

    moving_average: float = Field(..., ge=0, le=1)
    momentum: float = Field(..., ge=0, le=1)
    volume: float = Field(..., ge=0, le=1)
    volatility: float = Field(..., ge=0, le=1)
    fundamental: float = Field(..., ge=0, le=1)
    support_resistance: float = Field(..., ge=0, le=1)


class AnalysisMetadata(BaseModel):
    """Reproducibility metadata for an analysis run."""

    model_config = ConfigDict(frozen=True)

    config_hash: str = Field(..., description="Stable hash of ScoringConfig used")
    scoring_version: str = Field(..., description="Semver of scoring engine code")
    computed_at: datetime
    data_points_used: int = Field(..., ge=0)
    warnings: list[str] = Field(default_factory=list)


class StockAnalysis(BaseModel):
    """Full deterministic analysis output for one stock."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    moving_averages: MovingAverages
    features: Features
    score: float = Field(..., ge=0, le=1)
    sub_scores: SubScores
    signals: dict[str, bool | str]
    metadata: AnalysisMetadata

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
