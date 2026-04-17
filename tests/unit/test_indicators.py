"""Unit tests for pure indicator functions."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.processing.indicators import (
    atr,
    average_volume,
    classify_alignment,
    classify_slope,
    detect_crossover,
    distance_pct,
    ema,
    is_near,
    obv,
    period_return,
    price_to_ma_pct,
    rolling_std,
    rsi,
    sma,
    true_range,
    volume_ratio,
    window_52w,
)

# -------------------- SMA / EMA --------------------


def test_sma_requires_full_window() -> None:
    closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(closes, 3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_ema_converges_toward_constant_input() -> None:
    closes = pd.Series([10.0] * 50)
    assert ema(closes, 12).iloc[-1] == pytest.approx(10.0)


def test_sma_rejects_bad_period() -> None:
    with pytest.raises(ValueError):
        sma(pd.Series([1.0, 2.0]), 0)


def test_price_to_ma_pct_basic() -> None:
    assert price_to_ma_pct(110.0, 100.0) == pytest.approx(0.10)
    assert price_to_ma_pct(90.0, 100.0) == pytest.approx(-0.10)
    assert math.isnan(price_to_ma_pct(100.0, float("nan")))
    assert math.isnan(price_to_ma_pct(100.0, 0.0))


# -------------------- Crossover detection --------------------


def test_detect_crossover_golden() -> None:
    # short MA crosses above long MA on the last bar.
    short = pd.Series([8.0, 9.0, 10.0, 11.0])
    long_ma = pd.Series([10.0, 10.0, 10.0, 10.0])
    cross, days = detect_crossover(short, long_ma, lookback_days=3)
    assert cross == "golden_cross"
    assert days == 0  # happened on the latest bar


def test_detect_crossover_death() -> None:
    short = pd.Series([12.0, 11.0, 10.0, 9.0])
    long_ma = pd.Series([10.0, 10.0, 10.0, 10.0])
    cross, days = detect_crossover(short, long_ma, lookback_days=3)
    assert cross == "death_cross"
    assert days == 0


def test_detect_crossover_no_cross_in_window() -> None:
    short = pd.Series([8.0, 8.5, 9.0, 9.5])
    long_ma = pd.Series([10.0, 10.0, 10.0, 10.0])
    cross, days = detect_crossover(short, long_ma, lookback_days=3)
    assert cross is None and days is None


def test_detect_crossover_handles_nan_tail() -> None:
    short = pd.Series([float("nan"), float("nan"), 9.0])
    long_ma = pd.Series([10.0, 10.0, 10.0])
    cross, days = detect_crossover(short, long_ma, lookback_days=2)
    assert cross is None and days is None


# -------------------- Slope classification --------------------


def test_classify_slope_rising() -> None:
    s = pd.Series([100.0 + i for i in range(15)])
    assert classify_slope(s, 10, flat_threshold=0.005) == "rising"


def test_classify_slope_flat_within_threshold() -> None:
    s = pd.Series([100.0] * 15)
    assert classify_slope(s, 10, flat_threshold=0.005) == "flat"


def test_classify_slope_falling() -> None:
    s = pd.Series([100.0 - i for i in range(15)])
    assert classify_slope(s, 10, flat_threshold=0.005) == "falling"


def test_classify_slope_insufficient_data_returns_flat() -> None:
    assert classify_slope(pd.Series([1.0, 2.0]), 10, 0.005) == "flat"


# -------------------- Alignment --------------------


def test_classify_alignment_bullish() -> None:
    assert classify_alignment(
        price=110.0,
        sma_short=105.0,
        sma_med=100.0,
        sma_long=95.0,
        short_slope="rising",
        med_slope="rising",
        long_slope="rising",
    ) == "bullish"


def test_classify_alignment_bearish() -> None:
    assert classify_alignment(
        price=80.0, sma_short=85.0, sma_med=90.0, sma_long=95.0,
        short_slope="falling", med_slope="falling", long_slope="falling",
    ) == "bearish"


def test_classify_alignment_mixed_when_falling_despite_stack() -> None:
    # Stacked bullish but med is falling → mixed.
    assert classify_alignment(
        price=110.0, sma_short=105.0, sma_med=100.0, sma_long=95.0,
        short_slope="rising", med_slope="falling", long_slope="rising",
    ) == "mixed"


def test_classify_alignment_mixed_when_nan() -> None:
    assert classify_alignment(
        price=100.0, sma_short=float("nan"), sma_med=95.0, sma_long=90.0,
        short_slope="rising", med_slope="rising", long_slope="rising",
    ) == "mixed"


# -------------------- RSI --------------------


def test_rsi_flat_prices_is_nan() -> None:
    closes = pd.Series([100.0] * 30)
    assert math.isnan(rsi(closes, 14).iloc[-1])


def test_rsi_strictly_rising_trends_high() -> None:
    closes = pd.Series([100.0 + i for i in range(30)])
    # Monotonic up → all gains, no losses → RSI = 100.
    assert rsi(closes, 14).iloc[-1] == pytest.approx(100.0)


def test_rsi_strictly_falling_trends_low() -> None:
    closes = pd.Series([100.0 - i for i in range(30)])
    # Monotonic down → all losses, no gains → avg_gain = 0 → RSI = 0.
    result = rsi(closes, 14).iloc[-1]
    assert result == pytest.approx(0.0) or result < 5.0


def test_rsi_insufficient_data_is_nan() -> None:
    closes = pd.Series([100.0, 101.0, 102.0])
    assert math.isnan(rsi(closes, 14).iloc[-1])


def test_rsi_is_bounded_between_0_and_100() -> None:
    rng = np.random.default_rng(42)
    closes = pd.Series(100 + rng.standard_normal(100).cumsum())
    result = rsi(closes, 14).dropna()
    assert (result >= 0).all() and (result <= 100).all()


# -------------------- Returns --------------------


def test_period_return_basic() -> None:
    closes = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    assert period_return(closes, 5) == pytest.approx(0.05)


def test_period_return_insufficient_data() -> None:
    assert math.isnan(period_return(pd.Series([1.0, 2.0]), 5))


# -------------------- Volume --------------------


def test_volume_ratio_basic() -> None:
    assert volume_ratio(2000, 1000) == pytest.approx(2.0)


def test_volume_ratio_handles_zero_avg() -> None:
    assert math.isnan(volume_ratio(100, 0))


def test_average_volume_matches_sma() -> None:
    vols = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0])
    assert average_volume(vols, 3).iloc[-1] == pytest.approx(400.0)


def test_obv_up_and_down_days() -> None:
    closes = pd.Series([100.0, 101.0, 99.0, 100.0])
    volumes = pd.Series([10.0, 20.0, 30.0, 40.0])
    result = obv(closes, volumes)
    # bar 0: 0 (no prior); bar 1: +20 (up); bar 2: -30 (down); bar 3: +40 (up)
    assert result.iloc[-1] == pytest.approx(30.0)


def test_obv_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        obv(pd.Series([1.0, 2.0]), pd.Series([10.0]))


# -------------------- Volatility --------------------


def test_true_range_first_bar_uses_hl() -> None:
    highs = pd.Series([105.0, 110.0])
    lows = pd.Series([95.0, 100.0])
    closes = pd.Series([100.0, 108.0])
    tr = true_range(highs, lows, closes)
    assert tr.iloc[0] == pytest.approx(10.0)  # H - L (no prior close)
    assert tr.iloc[1] == pytest.approx(10.0)  # max(10, |110-100|, |100-100|)


def test_atr_nonneg_on_random_walk() -> None:
    rng = np.random.default_rng(1)
    closes = pd.Series(100 + rng.standard_normal(50).cumsum())
    highs = closes + rng.uniform(0, 2, 50)
    lows = closes - rng.uniform(0, 2, 50)
    result = atr(highs, lows, closes, 14).dropna()
    assert (result >= 0).all()


def test_rolling_std_positive() -> None:
    rng = np.random.default_rng(2)
    closes = pd.Series(100 + rng.standard_normal(50).cumsum())
    assert (rolling_std(closes, 20).dropna() > 0).all()


# -------------------- Support/Resistance --------------------


def test_window_52w_returns_tail_extremes() -> None:
    highs = pd.Series([100.0 + i for i in range(260)])
    lows = pd.Series([50.0 + i for i in range(260)])
    hi, lo = window_52w(highs, lows)
    assert hi == pytest.approx(259.0)
    assert lo == pytest.approx(58.0)  # 252 bars ago: index 8 → 50 + 8 = 58


def test_window_52w_fallback_to_available() -> None:
    highs = pd.Series([100.0, 105.0, 110.0])
    lows = pd.Series([90.0, 95.0, 98.0])
    hi, lo = window_52w(highs, lows)
    assert hi == pytest.approx(110.0)
    assert lo == pytest.approx(90.0)


def test_distance_pct_signed() -> None:
    assert distance_pct(95.0, 100.0) == pytest.approx(-0.05)
    assert distance_pct(105.0, 100.0) == pytest.approx(0.05)


def test_is_near_within_tolerance() -> None:
    assert is_near(99.0, 100.0, 0.02)
    assert not is_near(90.0, 100.0, 0.05)
