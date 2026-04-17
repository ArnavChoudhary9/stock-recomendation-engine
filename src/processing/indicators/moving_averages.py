"""Moving-average indicators: SMA, EMA, crossovers, alignment, slopes.

All functions accept close-price arrays (numpy ``ndarray`` or pandas ``Series``).
Results that require N data points return NaN for the first N-1 entries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.contracts import Alignment, Crossover, Slope


def sma(closes: pd.Series, period: int) -> pd.Series:
    """Simple moving average. Returns NaN for the first ``period - 1`` entries."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    return closes.rolling(window=period, min_periods=period).mean()


def ema(closes: pd.Series, period: int) -> pd.Series:
    """Exponential moving average (span convention, no adjust)."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    return closes.ewm(span=period, adjust=False, min_periods=period).mean()


def price_to_ma_pct(price: float, ma_value: float) -> float:
    """Signed percentage distance of ``price`` from ``ma_value``. ``(price/ma - 1)``."""
    if ma_value == 0 or np.isnan(ma_value):
        return float("nan")
    return (price / ma_value) - 1.0


def detect_crossover(
    short_ma: pd.Series, long_ma: pd.Series, lookback_days: int
) -> tuple[Crossover | None, int | None]:
    """Detect a golden/death cross within the last ``lookback_days`` bars.

    Returns (crossover_type, days_ago) — ``days_ago=0`` means the cross occurred
    on the latest bar. Returns (None, None) if no cross is found in the window.
    """
    if lookback_days <= 0:
        return None, None
    # Need at least lookback_days + 1 values to compare consecutive pairs.
    window_short = short_ma.tail(lookback_days + 1).to_numpy()
    window_long = long_ma.tail(lookback_days + 1).to_numpy()
    if len(window_short) < 2 or np.isnan(window_short).any() or np.isnan(window_long).any():
        return None, None

    # Walk from most recent backward so the first match is the most recent cross.
    n = len(window_short)
    for i in range(n - 1, 0, -1):
        prev_diff = window_short[i - 1] - window_long[i - 1]
        curr_diff = window_short[i] - window_long[i]
        if prev_diff <= 0 < curr_diff:
            return "golden_cross", (n - 1) - i
        if prev_diff >= 0 > curr_diff:
            return "death_cross", (n - 1) - i
    return None, None


def classify_slope(
    ma_series: pd.Series, slope_period: int, flat_threshold: float
) -> Slope:
    """Classify MA trend over ``slope_period`` bars as rising / falling / flat.

    Uses percentage change between the value N bars ago and the latest value.
    Defaults to ``"flat"`` if there isn't enough data.
    """
    if slope_period <= 0 or len(ma_series) <= slope_period:
        return "flat"
    latest = ma_series.iloc[-1]
    prior = ma_series.iloc[-1 - slope_period]
    if np.isnan(latest) or np.isnan(prior) or prior == 0:
        return "flat"
    pct_change = (latest / prior) - 1.0
    if abs(pct_change) < flat_threshold:
        return "flat"
    return "rising" if pct_change > 0 else "falling"


def classify_alignment(
    price: float,
    sma_short: float,
    sma_med: float,
    sma_long: float,
    short_slope: Slope,
    med_slope: Slope,
    long_slope: Slope,
) -> Alignment:
    """Return ``bullish`` / ``bearish`` / ``mixed`` for the MA stack.

    Bullish: price > short > med > long AND none of the MAs falling.
    Bearish: price < short < med < long AND none of the MAs rising.
    Otherwise mixed.
    """
    if any(np.isnan(v) for v in (sma_short, sma_med, sma_long)):
        return "mixed"
    if price > sma_short > sma_med > sma_long and "falling" not in (
        short_slope, med_slope, long_slope
    ):
        return "bullish"
    if price < sma_short < sma_med < sma_long and "rising" not in (
        short_slope, med_slope, long_slope
    ):
        return "bearish"
    return "mixed"
