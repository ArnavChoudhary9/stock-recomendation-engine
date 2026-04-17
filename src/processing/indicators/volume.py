"""Volume indicators: rolling average, volume ratio, OBV."""

from __future__ import annotations

import numpy as np
import pandas as pd


def average_volume(volumes: pd.Series, period: int) -> pd.Series:
    """Rolling mean of volume over ``period`` bars."""
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    return volumes.rolling(window=period, min_periods=period).mean()


def volume_ratio(current_volume: float, avg_volume: float) -> float:
    """``current / avg_volume``. Returns NaN if ``avg_volume`` is zero/NaN."""
    if avg_volume is None or np.isnan(avg_volume) or avg_volume == 0:
        return float("nan")
    return float(current_volume / avg_volume)


def obv(closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """On-Balance Volume: signed cumulative volume based on close-direction.

    Up day → + volume; down day → - volume; flat → 0. The first bar
    contributes 0 (no prior close for comparison).
    """
    if len(closes) != len(volumes):
        raise ValueError("closes and volumes must be the same length")
    if len(closes) == 0:
        return pd.Series(dtype=float)
    direction = np.sign(closes.diff().fillna(0.0))
    signed_volume = volumes * direction
    result: pd.Series = signed_volume.cumsum()
    return result
