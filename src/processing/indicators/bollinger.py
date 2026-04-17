"""Bollinger Bands — volatility envelope around a moving average.

``middle`` = SMA(period)
``upper``  = middle + std_dev * rolling_std(period)
``lower``  = middle - std_dev * rolling_std(period)
``%B``     = (price - lower) / (upper - lower), roughly in [0, 1]
``bandwidth`` = (upper - lower) / middle — a volatility proxy
"""

from __future__ import annotations

import math

import pandas as pd

from src.processing.indicators.moving_averages import sma


def bollinger_bands(
    closes: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return ``(upper, middle, lower)`` bands."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if std_dev <= 0:
        raise ValueError(f"std_dev must be positive, got {std_dev}")

    middle = sma(closes, period)
    std = closes.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def percent_b(price: float, upper: float, lower: float) -> float:
    """Fractional position of ``price`` inside the band envelope."""
    if math.isnan(upper) or math.isnan(lower):
        return float("nan")
    width = upper - lower
    if width <= 0:
        return 0.5
    return (price - lower) / width


def bandwidth(upper: float, middle: float, lower: float) -> float:
    """Relative band width; low values indicate a volatility squeeze."""
    if math.isnan(upper) or math.isnan(middle) or math.isnan(lower) or middle == 0:
        return float("nan")
    return (upper - lower) / middle
