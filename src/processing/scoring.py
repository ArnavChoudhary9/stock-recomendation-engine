"""Deterministic scoring engine.

Each feature group maps to a sub-score in [0, 1]; the final score is the
weighted average per :class:`ScoringWeights`. Missing inputs collapse the
corresponding sub-score to a neutral 0.5 so a single missing value doesn't
wipe out the ranking.
"""

from __future__ import annotations

import math
from typing import Final

from src.contracts import (
    Features,
    FundamentalFeatures,
    Momentum,
    MovingAverages,
    Recommendation,
    ScoringWeights,
    SubScores,
    SupportResistance,
    Volatility,
    VolumeFeatures,
)

SCORING_VERSION: Final[str] = "1.0.0"
_NEUTRAL: Final[float] = 0.5


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if math.isnan(x):
        return _NEUTRAL
    return max(lo, min(hi, x))


def ma_sub_score(ma: MovingAverages, last_close: float) -> float:
    """Combine alignment, crossover recency, and price/SMA200 distance into [0, 1]."""
    alignment_score = {"bullish": 1.0, "bearish": 0.0, "mixed": 0.5}[ma.alignment]

    crossover_bonus = 0.0
    if ma.crossover == "golden_cross":
        crossover_bonus = 0.2
    elif ma.crossover == "death_cross":
        crossover_bonus = -0.2

    # Position vs SMA(200): linearly map [-20%, +20%] → [0, 1].
    distance = ma.price_to_sma200_pct
    distance_score = _clamp(0.5 + distance * 2.5)  # 2.5 = 0.5 / 0.20

    combined = 0.5 * alignment_score + 0.3 * distance_score + 0.2 * (0.5 + crossover_bonus)
    return _clamp(combined)


def momentum_sub_score(m: Momentum) -> float:
    """RSI sweet spot 50-70 scores highest; positive returns boost."""
    rsi = m.rsi_14
    if math.isnan(rsi):
        rsi_component = _NEUTRAL
    elif 50.0 <= rsi <= 70.0:
        rsi_component = 1.0
    elif rsi < 50.0:
        # Ramp from 0 (at RSI=0) to 1 (at RSI=50).
        rsi_component = _clamp(rsi / 50.0)
    else:
        # Above 70: linearly decay to 0 at RSI=100.
        rsi_component = _clamp(1.0 - (rsi - 70.0) / 30.0)

    # Returns: +20% over 20d → 1.0; -20% → 0.0. Weighted toward longer horizons.
    def return_score(r: float) -> float:
        if math.isnan(r):
            return _NEUTRAL
        return _clamp(0.5 + r * 2.5)

    returns_component = (
        0.2 * return_score(m.return_5d)
        + 0.3 * return_score(m.return_10d)
        + 0.5 * return_score(m.return_20d)
    )

    return _clamp(0.6 * rsi_component + 0.4 * returns_component)


def volume_sub_score(v: VolumeFeatures) -> float:
    """Volume ratio 1.0 = neutral, 2.0+ = strong confirmation, <0.5 = anemic."""
    if math.isnan(v.volume_ratio):
        return _NEUTRAL
    # Map ratio 0.5 → 0.0, 1.0 → 0.5, 2.0 → 1.0.
    score = (v.volume_ratio - 0.5) / 1.5
    return _clamp(score)


def volatility_sub_score(vol: Volatility, last_close: float) -> float:
    """Lower normalized volatility (ATR/price) scores higher. 0% → 1.0, 5% → 0.0."""
    if last_close <= 0 or math.isnan(vol.atr_14):
        return _NEUTRAL
    normalized_atr = vol.atr_14 / last_close
    return _clamp(1.0 - normalized_atr / 0.05)


def fundamental_sub_score(f: FundamentalFeatures) -> float:
    """PE, ROE, market-cap tier — mean of whatever sub-signals are available."""
    parts: list[float] = []

    if f.pe_vs_sector_median is not None:
        # Negative = cheaper than sector = good. Map [-0.5, +0.5] → [1.0, 0.0].
        parts.append(_clamp(0.5 - f.pe_vs_sector_median))
    elif f.pe is not None and f.pe > 0:
        # Absolute PE fallback: PE 10 → 1.0, PE 40 → 0.0.
        parts.append(_clamp(1.0 - (f.pe - 10.0) / 30.0))

    if f.roe_sector_rank is not None:
        parts.append(_clamp(f.roe_sector_rank))
    elif f.roe is not None:
        # Absolute ROE fallback: 0% → 0, 25%+ → 1.0.
        parts.append(_clamp(f.roe / 0.25))

    if f.market_cap_tier is not None:
        tier_score = {"large": 0.9, "mid": 0.7, "small": 0.4, "micro": 0.2}
        parts.append(tier_score[f.market_cap_tier])

    if not parts:
        return _NEUTRAL
    return _clamp(sum(parts) / len(parts))


def support_resistance_sub_score(sr: SupportResistance) -> float:
    """Prefer stocks mid-range, with a slight bias toward strength near highs."""
    # distance_to_52w_high_pct is <= 0 (below high). Map -50% → 0.3, 0% → 0.8.
    near_high = sr.distance_to_52w_high_pct
    base = _clamp(0.8 + near_high * 1.0)  # 0% off high → 0.8; -50% → 0.3
    # But exactly at high can be overbought; penalise a bit.
    if sr.near_52w_high:
        base = min(base, 0.75)
    # Near 52w low — floor at 0.3 unless well above low.
    if sr.near_52w_low:
        base = max(base, 0.3)
    return _clamp(base)


def compute_sub_scores(features: Features) -> SubScores:
    """Produce every sub-score for a feature bundle. Pure function."""
    return SubScores(
        moving_average=ma_sub_score(features.moving_averages, features.last_close),
        momentum=momentum_sub_score(features.momentum),
        volume=volume_sub_score(features.volume),
        volatility=volatility_sub_score(features.volatility, features.last_close),
        fundamental=fundamental_sub_score(features.fundamentals),
        support_resistance=support_resistance_sub_score(features.support_resistance),
    )


def compose_score(sub_scores: SubScores, weights: ScoringWeights) -> float:
    """Weighted composite normalised by ``weights.total()`` (handles non-unit sums)."""
    total = weights.total()
    if total == 0:
        return _NEUTRAL
    weighted_sum = (
        sub_scores.moving_average * weights.moving_average
        + sub_scores.momentum * weights.momentum
        + sub_scores.volume * weights.volume
        + sub_scores.volatility * weights.volatility
        + sub_scores.fundamental * weights.fundamental
        + sub_scores.support_resistance * weights.support_resistance
    )
    return _clamp(weighted_sum / total)


# Composite-score bands for BUY/HOLD/SELL. The wide HOLD band [0.40, 0.60]
# stops noisy mid-range stocks from thrashing between calls run-to-run.
_BUY_SCORE_THRESHOLD: Final[float] = 0.60
_SELL_SCORE_THRESHOLD: Final[float] = 0.40


def derive_recommendation(
    score: float,
    sub_scores: SubScores,
    fundamentals: FundamentalFeatures,
    signals: dict[str, bool | str],
) -> tuple[Recommendation, str]:
    """Map the deterministic analysis to a BUY/HOLD/SELL with a one-line rationale.

    Fundamentals hold veto power both ways: strong fundamentals (sub >= 0.70)
    can lift a HOLD to BUY, and weak fundamentals (sub <= 0.30) can drop a
    HOLD to SELL. Technical red flags — ``death_cross``, ``overbought``,
    ``ma_bearish_stack`` — cap any BUY back to HOLD.
    """
    fund_strong = sub_scores.fundamental >= 0.70
    fund_weak = sub_scores.fundamental <= 0.30

    death_cross = signals.get("death_cross") is True
    golden_cross = signals.get("golden_cross") is True
    overbought = signals.get("overbought") is True
    bullish_stack = signals.get("ma_bullish_stack") is True
    bearish_stack = signals.get("ma_bearish_stack") is True

    if score >= _BUY_SCORE_THRESHOLD:
        base: Recommendation = "BUY"
    elif score <= _SELL_SCORE_THRESHOLD:
        base = "SELL"
    else:
        base = "HOLD"

    # Technical safety overrides first.
    if base == "BUY" and (death_cross or overbought or bearish_stack):
        base = "HOLD"

    # Fundamentals tip the decision inside the HOLD band.
    if base == "HOLD":
        if fund_strong and score >= 0.50 and not (death_cross or overbought):
            base = "BUY"
        elif fund_weak and score <= 0.50 and not golden_cross:
            base = "SELL"

    rationale_parts: list[str] = [
        f"composite {score:.2f}",
        f"fundamentals {sub_scores.fundamental:.2f}",
    ]
    if golden_cross and base == "BUY":
        rationale_parts.append("golden cross confirms trend")
    if death_cross:
        rationale_parts.append("death cross caps upside")
    if overbought:
        rationale_parts.append("RSI overbought")
    if bullish_stack:
        rationale_parts.append("MA stack bullish")
    if bearish_stack:
        rationale_parts.append("MA stack bearish")
    if fundamentals.pe_vs_sector_median is not None:
        tag = "cheap" if fundamentals.pe_vs_sector_median < 0 else "rich"
        rationale_parts.append(
            f"PE {tag} vs sector ({fundamentals.pe_vs_sector_median:+.2f})"
        )

    return base, "; ".join(rationale_parts)
