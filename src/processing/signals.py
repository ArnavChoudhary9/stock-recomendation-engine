"""Signal generator — boolean/categorical flags derived from :class:`Features`.

Every signal listed in the PRD's signal table maps to a key in the returned
dict. Values are ``bool`` except crossover entries which use the literal names.
"""

from __future__ import annotations

import math

from src.contracts import Features, SignalThresholds


def generate_signals(features: Features, thresholds: SignalThresholds) -> dict[str, bool | str]:
    """Produce the canonical signal dict. Pure function of ``features`` + thresholds."""
    ma = features.moving_averages
    m = features.momentum
    v = features.volume
    sr = features.support_resistance

    signals: dict[str, bool | str] = {}

    # Crossovers (mutually exclusive). Report both booleans + a categorical label.
    in_window = (
        ma.crossover is not None
        and ma.crossover_days_ago is not None
        and ma.crossover_days_ago <= thresholds.crossover_lookback_days
    )
    signals["golden_cross"] = in_window and ma.crossover == "golden_cross"
    signals["death_cross"] = in_window and ma.crossover == "death_cross"

    # Stacking — requires full alignment AND correct slope direction.
    signals["ma_bullish_stack"] = (
        ma.alignment == "bullish"
        and ma.sma50_slope == "rising"
        and ma.sma200_slope == "rising"
    )
    signals["ma_bearish_stack"] = (
        ma.alignment == "bearish"
        and ma.sma50_slope == "falling"
        and ma.sma200_slope == "falling"
    )

    # Price vs SMA(200).
    above_200 = features.last_close > ma.sma_200 if not math.isnan(ma.sma_200) else False
    signals["price_above_200sma"] = above_200
    signals["price_below_200sma"] = not above_200 and not math.isnan(ma.sma_200)

    # Momentum regime.
    rsi = m.rsi_14
    signals["overbought"] = not math.isnan(rsi) and rsi > thresholds.rsi_overbought
    signals["oversold"] = not math.isnan(rsi) and rsi < thresholds.rsi_oversold
    signals["momentum_strong"] = (
        not math.isnan(rsi)
        and thresholds.rsi_oversold <= rsi <= thresholds.rsi_overbought
        and 50.0 <= rsi <= 70.0
        and not math.isnan(m.return_5d)
        and m.return_5d > 0
    )

    # Volume spike.
    signals["volume_spike"] = (
        not math.isnan(v.volume_ratio)
        and v.volume_ratio >= thresholds.volume_spike_multiplier
    )

    # 52-week proximity.
    signals["near_52w_high"] = sr.near_52w_high
    signals["near_52w_low"] = sr.near_52w_low

    # MACD crossovers (fires only within the configured lookback window).
    if features.macd is not None:
        in_macd_window = (
            features.macd.crossover is not None
            and features.macd.crossover_days_ago is not None
            and features.macd.crossover_days_ago <= thresholds.macd_crossover_lookback_days
        )
        signals["macd_bullish_cross"] = (
            in_macd_window and features.macd.crossover == "bullish"
        )
        signals["macd_bearish_cross"] = (
            in_macd_window and features.macd.crossover == "bearish"
        )
        signals["macd_positive_histogram"] = features.macd.histogram > 0
    else:
        signals["macd_bullish_cross"] = False
        signals["macd_bearish_cross"] = False
        signals["macd_positive_histogram"] = False

    # Bollinger regime.
    if features.bollinger is not None:
        bb = features.bollinger
        eps = thresholds.bollinger_breakout_epsilon
        signals["bb_squeeze"] = bb.squeeze
        signals["bb_breakout_upper"] = features.last_close >= bb.upper * (1 - eps)
        signals["bb_breakout_lower"] = features.last_close <= bb.lower * (1 + eps)
    else:
        signals["bb_squeeze"] = False
        signals["bb_breakout_upper"] = False
        signals["bb_breakout_lower"] = False

    return signals
