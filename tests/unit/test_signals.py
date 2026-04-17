"""Unit tests for the signal generator."""

from __future__ import annotations

from datetime import UTC, datetime

from src.contracts import (
    Features,
    FundamentalFeatures,
    Momentum,
    MovingAverages,
    SignalThresholds,
    SupportResistance,
    Volatility,
    VolumeFeatures,
)
from src.processing.signals import generate_signals


def _feature_bundle(**ma_overrides) -> Features:  # type: ignore[no-untyped-def]
    ma_defaults = dict(
        sma_20=100.0, sma_50=98.0, sma_200=95.0,
        ema_12=99.0, ema_26=97.0,
        price_to_sma20_pct=0.01, price_to_sma50_pct=0.03, price_to_sma200_pct=0.05,
        alignment="bullish", sma50_slope="rising", sma200_slope="rising",
        crossover=None, crossover_days_ago=None,
    )
    ma_defaults.update(ma_overrides)
    return Features(
        symbol="TEST",
        as_of=datetime.now(UTC),
        last_close=101.0,
        moving_averages=MovingAverages(**ma_defaults),  # type: ignore[arg-type]
        momentum=Momentum(rsi_14=60.0, return_5d=0.02, return_10d=0.04, return_20d=0.08),
        volume=VolumeFeatures(current_volume=1500, avg_volume_20d=1000.0,
                              volume_ratio=1.5, obv=50000.0),
        volatility=Volatility(atr_14=2.0, std_dev_20=1.5),
        fundamentals=FundamentalFeatures(),
        support_resistance=SupportResistance(
            high_52w=150.0, low_52w=80.0,
            distance_to_52w_high_pct=-0.15, distance_to_52w_low_pct=0.60,
            near_52w_high=False, near_52w_low=False,
        ),
    )


def test_golden_cross_within_window() -> None:
    f = _feature_bundle(crossover="golden_cross", crossover_days_ago=2)
    s = generate_signals(f, SignalThresholds())
    assert s["golden_cross"] is True
    assert s["death_cross"] is False


def test_golden_cross_outside_window_ignored() -> None:
    f = _feature_bundle(crossover="golden_cross", crossover_days_ago=20)
    s = generate_signals(f, SignalThresholds(crossover_lookback_days=5))
    assert s["golden_cross"] is False


def test_bullish_stack_requires_rising_slopes() -> None:
    f_bullish = _feature_bundle(alignment="bullish", sma50_slope="rising", sma200_slope="rising")
    assert generate_signals(f_bullish, SignalThresholds())["ma_bullish_stack"] is True

    f_flat = _feature_bundle(alignment="bullish", sma50_slope="flat", sma200_slope="rising")
    assert generate_signals(f_flat, SignalThresholds())["ma_bullish_stack"] is False


def test_price_above_vs_below_200sma() -> None:
    f_above = _feature_bundle()
    s = generate_signals(f_above, SignalThresholds())
    assert s["price_above_200sma"] is True
    assert s["price_below_200sma"] is False


def test_overbought_oversold_flags() -> None:
    thresh = SignalThresholds()
    assert generate_signals(_feature_bundle_rsi(75.0), thresh)["overbought"] is True
    assert generate_signals(_feature_bundle_rsi(25.0), thresh)["oversold"] is True
    assert generate_signals(_feature_bundle_rsi(55.0), thresh)["overbought"] is False


def test_volume_spike_threshold() -> None:
    thresh = SignalThresholds(volume_spike_multiplier=2.0)
    f_spike = _feature_bundle()
    # Replace the volume features with a spike.
    f_spike = f_spike.model_copy(
        update={"volume": VolumeFeatures(
            current_volume=3000, avg_volume_20d=1000.0, volume_ratio=3.0, obv=50000.0,
        )}
    )
    assert generate_signals(f_spike, thresh)["volume_spike"] is True


def _feature_bundle_rsi(rsi: float) -> Features:
    f = _feature_bundle()
    return f.model_copy(update={
        "momentum": Momentum(rsi_14=rsi, return_5d=0.01, return_10d=0.02, return_20d=0.03)
    })
