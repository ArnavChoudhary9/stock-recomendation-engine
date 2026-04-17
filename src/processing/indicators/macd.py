"""MACD — Moving Average Convergence Divergence.

``macd_line``   = EMA(fast) - EMA(slow)
``signal_line`` = EMA(signal_period) of ``macd_line``
``histogram``   = macd_line - signal_line

Crossover detection walks the most recent ``lookback_days`` bars and returns
the latest bullish (``macd_line`` crosses above ``signal_line``) or bearish
(opposite) crossover, along with how many days ago it occurred.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from src.processing.indicators.moving_averages import ema

MACDCrossover = Literal["bullish", "bearish"]


def macd(
    closes: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return ``(macd_line, signal_line, histogram)`` series."""
    if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
        raise ValueError("All MACD periods must be positive")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be < slow_period")

    fast = ema(closes, fast_period)
    slow = ema(closes, slow_period)
    macd_line = fast - slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def detect_macd_crossover(
    macd_line: pd.Series,
    signal_line: pd.Series,
    lookback_days: int,
) -> tuple[MACDCrossover | None, int | None]:
    """Find the most recent MACD signal-line crossover within ``lookback_days``."""
    if lookback_days <= 0:
        return None, None
    window_macd = macd_line.tail(lookback_days + 1).to_numpy()
    window_signal = signal_line.tail(lookback_days + 1).to_numpy()
    if (
        len(window_macd) < 2
        or np.isnan(window_macd).any()
        or np.isnan(window_signal).any()
    ):
        return None, None

    n = len(window_macd)
    for i in range(n - 1, 0, -1):
        prev_diff = window_macd[i - 1] - window_signal[i - 1]
        curr_diff = window_macd[i] - window_signal[i]
        if prev_diff <= 0 < curr_diff:
            return "bullish", (n - 1) - i
        if prev_diff >= 0 > curr_diff:
            return "bearish", (n - 1) - i
    return None, None
