"""Feature computation — assembles :class:`Features` from raw OHLCV + fundamentals.

Pure function with no I/O: takes a list of :class:`OHLCVRow` (ascending by date)
plus optional fundamentals/stock-info, produces a :class:`Features` bundle.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.contracts import (
    Features,
    FundamentalFeatures,
    Fundamentals,
    IndicatorPeriods,
    MarketCapTier,
    Momentum,
    MovingAverages,
    OHLCVRow,
    SignalThresholds,
    StockInfo,
    SupportResistance,
    Volatility,
    VolumeFeatures,
)
from src.processing.indicators import (
    atr,
    average_volume,
    classify_alignment,
    classify_slope,
    detect_crossover,
    distance_pct,
    ema,
    is_near,
    latest_or_nan,
    obv,
    period_return,
    price_to_ma_pct,
    rolling_std,
    rsi,
    sma,
    volume_ratio,
    window_52w,
)


class InsufficientDataError(Exception):
    """Raised when fewer bars are available than the longest required indicator window."""


def ohlcv_to_dataframe(rows: list[OHLCVRow]) -> pd.DataFrame:
    """Convert contract rows to a date-indexed DataFrame. Sorts ascending."""
    if not rows:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([], name="date"),
        )
    data = {
        "open": [r.open for r in rows],
        "high": [r.high for r in rows],
        "low": [r.low for r in rows],
        "close": [r.close for r in rows],
        "volume": [r.volume for r in rows],
    }
    idx = pd.DatetimeIndex([pd.Timestamp(r.date) for r in rows], name="date")
    df = pd.DataFrame(data, index=idx)
    return df.sort_index()


def _classify_market_cap(market_cap: float | None) -> MarketCapTier | None:
    """Indian convention: >200B INR = large, 50B-200B = mid, 5B-50B = small, else micro."""
    if market_cap is None or market_cap <= 0:
        return None
    if market_cap >= 200e9:
        return "large"
    if market_cap >= 50e9:
        return "mid"
    if market_cap >= 5e9:
        return "small"
    return "micro"


def _moving_averages(
    closes: pd.Series,
    last_close: float,
    periods: IndicatorPeriods,
    thresholds: SignalThresholds,
) -> MovingAverages:
    sma_periods = sorted(periods.sma_periods)
    if len(sma_periods) < 3:
        raise ValueError(f"Need at least 3 SMA periods, got {periods.sma_periods}")
    short_p, med_p, long_p = sma_periods[0], sma_periods[1], sma_periods[2]
    ema_periods = sorted(periods.ema_periods)
    if len(ema_periods) < 2:
        raise ValueError(f"Need at least 2 EMA periods, got {periods.ema_periods}")

    sma_short = sma(closes, short_p)
    sma_med = sma(closes, med_p)
    sma_long = sma(closes, long_p)
    ema_short = ema(closes, ema_periods[0])
    ema_long = ema(closes, ema_periods[1])

    sma_short_v = latest_or_nan(sma_short)
    sma_med_v = latest_or_nan(sma_med)
    sma_long_v = latest_or_nan(sma_long)

    if math.isnan(sma_long_v):
        raise InsufficientDataError(
            f"Need at least {long_p} bars for SMA({long_p}); got {len(closes)}"
        )

    med_slope = classify_slope(sma_med, thresholds.ma_slope_period, thresholds.ma_slope_flat_threshold)
    long_slope = classify_slope(sma_long, thresholds.ma_slope_period, thresholds.ma_slope_flat_threshold)
    short_slope = classify_slope(sma_short, thresholds.ma_slope_period, thresholds.ma_slope_flat_threshold)

    crossover, days_ago = detect_crossover(sma_med, sma_long, thresholds.crossover_lookback_days)
    alignment = classify_alignment(
        last_close, sma_short_v, sma_med_v, sma_long_v, short_slope, med_slope, long_slope
    )

    return MovingAverages(
        sma_20=sma_short_v,
        sma_50=sma_med_v,
        sma_200=sma_long_v,
        ema_12=latest_or_nan(ema_short),
        ema_26=latest_or_nan(ema_long),
        price_to_sma20_pct=price_to_ma_pct(last_close, sma_short_v),
        price_to_sma50_pct=price_to_ma_pct(last_close, sma_med_v),
        price_to_sma200_pct=price_to_ma_pct(last_close, sma_long_v),
        alignment=alignment,
        sma50_slope=med_slope,
        sma200_slope=long_slope,
        crossover=crossover,
        crossover_days_ago=days_ago,
    )


def _momentum(closes: pd.Series, periods: IndicatorPeriods) -> Momentum:
    rsi_val = latest_or_nan(rsi(closes, periods.rsi_period))
    mom_periods = sorted(periods.momentum_periods)
    if len(mom_periods) < 3:
        raise ValueError(f"Need at least 3 momentum periods, got {periods.momentum_periods}")
    return Momentum(
        rsi_14=0.0 if math.isnan(rsi_val) else rsi_val,
        return_5d=period_return(closes, mom_periods[0]),
        return_10d=period_return(closes, mom_periods[1]),
        return_20d=period_return(closes, mom_periods[2]),
    )


def _volume(df: pd.DataFrame, periods: IndicatorPeriods) -> VolumeFeatures:
    volumes = df["volume"].astype(float)
    avg = average_volume(volumes, periods.volume_avg_period)
    current = float(volumes.iloc[-1])
    avg_latest = latest_or_nan(avg)
    ratio = volume_ratio(current, avg_latest)
    obv_series = obv(df["close"], volumes)
    return VolumeFeatures(
        current_volume=int(current),
        avg_volume_20d=0.0 if math.isnan(avg_latest) else avg_latest,
        volume_ratio=0.0 if math.isnan(ratio) else ratio,
        obv=latest_or_nan(obv_series) if not math.isnan(latest_or_nan(obv_series)) else 0.0,
    )


def _volatility(df: pd.DataFrame, periods: IndicatorPeriods) -> Volatility:
    atr_series = atr(df["high"], df["low"], df["close"], periods.atr_period)
    std_series = rolling_std(df["close"], periods.volatility_period)
    atr_latest = latest_or_nan(atr_series)
    std_latest = latest_or_nan(std_series)
    return Volatility(
        atr_14=0.0 if math.isnan(atr_latest) else atr_latest,
        std_dev_20=0.0 if math.isnan(std_latest) else std_latest,
    )


def _fundamentals(
    fundamentals: Fundamentals | None,
) -> FundamentalFeatures:
    if fundamentals is None:
        return FundamentalFeatures()
    return FundamentalFeatures(
        pe=fundamentals.pe,
        pe_vs_sector_median=None,  # filled in batch-ranking phase when peers are known
        market_cap=fundamentals.market_cap,
        market_cap_tier=_classify_market_cap(fundamentals.market_cap),
        roe=fundamentals.roe,
        roe_sector_rank=None,
    )


def _support_resistance(
    df: pd.DataFrame, last_close: float, thresholds: SignalThresholds
) -> SupportResistance:
    hi, lo = window_52w(df["high"], df["low"])
    if np.isnan(hi) or np.isnan(lo):
        raise InsufficientDataError("No high/low data available for 52w window")
    return SupportResistance(
        high_52w=hi,
        low_52w=lo,
        distance_to_52w_high_pct=distance_pct(last_close, hi),
        distance_to_52w_low_pct=distance_pct(last_close, lo),
        near_52w_high=is_near(last_close, hi, thresholds.near_high_low_pct),
        near_52w_low=is_near(last_close, lo, thresholds.near_high_low_pct),
    )


def compute_features(
    symbol: str,
    ohlcv: list[OHLCVRow],
    fundamentals: Fundamentals | None,
    periods: IndicatorPeriods,
    thresholds: SignalThresholds,
    stock_info: StockInfo | None = None,
) -> Features:
    """Build a full :class:`Features` bundle for ``symbol`` from raw bars.

    Raises :class:`InsufficientDataError` when too few bars are present for the
    longest configured indicator (typically SMA(200)).
    """
    del stock_info  # reserved for future sector-relative features
    df = ohlcv_to_dataframe(ohlcv)
    if df.empty:
        raise InsufficientDataError(f"No OHLCV bars for {symbol}")

    closes = df["close"].astype(float)
    last_close = float(closes.iloc[-1])

    return Features(
        symbol=symbol,
        as_of=datetime.now(UTC),
        last_close=last_close,
        moving_averages=_moving_averages(closes, last_close, periods, thresholds),
        momentum=_momentum(closes, periods),
        volume=_volume(df, periods),
        volatility=_volatility(df, periods),
        fundamentals=_fundamentals(fundamentals),
        support_resistance=_support_resistance(df, last_close, thresholds),
    )
