"""52-week high/low and proximity metrics."""

from __future__ import annotations

import pandas as pd

_TRADING_DAYS_52W = 252


def window_52w(highs: pd.Series, lows: pd.Series) -> tuple[float, float]:
    """Return (high_52w, low_52w) over the trailing 252 trading days.

    Falls back to whatever data is available if fewer than 252 bars exist.
    """
    window = min(len(highs), _TRADING_DAYS_52W)
    if window == 0:
        return float("nan"), float("nan")
    h = float(highs.tail(window).max())
    lo = float(lows.tail(window).min())
    return h, lo


def distance_pct(price: float, level: float) -> float:
    """Signed percentage distance of ``price`` from ``level``. ``(price/level - 1)``."""
    if level == 0:
        return float("nan")
    return (price / level) - 1.0


def is_near(price: float, level: float, tolerance: float) -> bool:
    """True if ``|price/level - 1| <= tolerance`` (e.g. 0.05 = within 5%)."""
    if level == 0:
        return False
    return abs((price / level) - 1.0) <= tolerance
