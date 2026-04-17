"""Volatility indicators: ATR (Wilder) and rolling standard deviation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(highs: pd.Series, lows: pd.Series, closes: pd.Series) -> pd.Series:
    """True range = max(H-L, |H - prev_C|, |L - prev_C|).

    The first bar has no prior close, so TR = H - L there.
    """
    prev_close = closes.shift(1)
    hl = highs - lows
    hc = (highs - prev_close).abs()
    lc = (lows - prev_close).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)


def atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's smoothed average true range (``alpha = 1/period``)."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    tr = true_range(highs, lows, closes)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rolling_std(closes: pd.Series, period: int) -> pd.Series:
    """Sample standard deviation of close prices over ``period`` bars."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    return closes.rolling(window=period, min_periods=period).std(ddof=1)


def latest_or_nan(series: pd.Series) -> float:
    """Return the last value of a series, or NaN for empty/NaN-tail series."""
    if len(series) == 0:
        return float("nan")
    v = series.iloc[-1]
    return float(v) if not np.isnan(v) else float("nan")
