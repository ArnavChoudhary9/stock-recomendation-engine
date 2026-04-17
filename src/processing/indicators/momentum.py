"""Momentum indicators: RSI and period returns."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI — uses exponentially weighted moving avg of gains/losses.

    RSI is undefined until ``period + 1`` bars exist (need ``period`` diffs).
    The first ``period`` values of the output will be NaN.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    delta = closes.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    # Wilder uses alpha = 1/period equivalently via ewm(alpha=...).
    avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss is 0 and avg_gain > 0, RS is inf → RSI = 100.
    rsi_series = rsi_series.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    # When both are 0 (flat prices), RSI is undefined — leave NaN.
    return rsi_series


def period_return(closes: pd.Series, days: int) -> float:
    """Return ``close_today / close_N_days_ago - 1``, or NaN if insufficient data."""
    if days <= 0:
        raise ValueError(f"days must be positive, got {days}")
    if len(closes) <= days:
        return float("nan")
    prior = closes.iloc[-1 - days]
    latest = closes.iloc[-1]
    if prior == 0 or np.isnan(prior) or np.isnan(latest):
        return float("nan")
    return float((latest / prior) - 1.0)
