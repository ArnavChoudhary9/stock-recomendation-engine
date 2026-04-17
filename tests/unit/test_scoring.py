"""Unit + property tests for the scoring engine."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.contracts import (
    Features,
    FundamentalFeatures,
    Momentum,
    MovingAverages,
    ScoringWeights,
    SubScores,
    SupportResistance,
    Volatility,
    VolumeFeatures,
)
from src.processing.scoring import (
    compose_score,
    compute_sub_scores,
    fundamental_sub_score,
    ma_sub_score,
    momentum_sub_score,
    support_resistance_sub_score,
    volatility_sub_score,
    volume_sub_score,
)


def _ma(**kwargs) -> MovingAverages:  # type: ignore[no-untyped-def]
    defaults = dict(
        sma_20=100.0, sma_50=98.0, sma_200=95.0,
        ema_12=99.0, ema_26=97.0,
        price_to_sma20_pct=0.01, price_to_sma50_pct=0.03, price_to_sma200_pct=0.05,
        alignment="bullish", sma50_slope="rising", sma200_slope="rising",
        crossover=None, crossover_days_ago=None,
    )
    defaults.update(kwargs)
    return MovingAverages(**defaults)  # type: ignore[arg-type]


def _momentum(**kwargs) -> Momentum:  # type: ignore[no-untyped-def]
    defaults = dict(rsi_14=60.0, return_5d=0.02, return_10d=0.04, return_20d=0.08)
    defaults.update(kwargs)
    return Momentum(**defaults)


def _volume(**kwargs) -> VolumeFeatures:  # type: ignore[no-untyped-def]
    defaults: dict[str, object] = dict(
        current_volume=1500, avg_volume_20d=1000.0, volume_ratio=1.5, obv=50000.0,
    )
    defaults.update(kwargs)
    return VolumeFeatures(**defaults)  # type: ignore[arg-type]


def _volatility(**kwargs) -> Volatility:  # type: ignore[no-untyped-def]
    defaults = dict(atr_14=2.0, std_dev_20=1.5)
    defaults.update(kwargs)
    return Volatility(**defaults)


def _sr(**kwargs) -> SupportResistance:  # type: ignore[no-untyped-def]
    defaults = dict(
        high_52w=150.0, low_52w=80.0,
        distance_to_52w_high_pct=-0.15, distance_to_52w_low_pct=0.60,
        near_52w_high=False, near_52w_low=False,
    )
    defaults.update(kwargs)
    return SupportResistance(**defaults)  # type: ignore[arg-type]


def _features(**overrides) -> Features:  # type: ignore[no-untyped-def]
    base = dict(
        symbol="TEST",
        as_of=datetime.now(UTC),
        last_close=100.0,
        moving_averages=_ma(),
        momentum=_momentum(),
        volume=_volume(),
        volatility=_volatility(),
        fundamentals=FundamentalFeatures(),
        support_resistance=_sr(),
    )
    base.update(overrides)
    return Features(**base)  # type: ignore[arg-type]


# -------------------- MA sub-score --------------------


def test_ma_sub_score_bullish_plus_golden_cross_high() -> None:
    ma = _ma(alignment="bullish", crossover="golden_cross", crossover_days_ago=1,
             price_to_sma200_pct=0.10)
    assert ma_sub_score(ma, last_close=100.0) > 0.7


def test_ma_sub_score_bearish_plus_death_cross_low() -> None:
    ma = _ma(alignment="bearish", crossover="death_cross", crossover_days_ago=0,
             price_to_sma200_pct=-0.10)
    assert ma_sub_score(ma, last_close=100.0) < 0.3


def test_ma_sub_score_always_in_unit_range() -> None:
    for alignment in ("bullish", "bearish", "mixed"):
        ma = _ma(alignment=alignment, price_to_sma200_pct=-0.5)
        s = ma_sub_score(ma, last_close=100.0)
        assert 0.0 <= s <= 1.0


# -------------------- Momentum sub-score --------------------


def test_momentum_sub_score_sweet_spot_rsi_high() -> None:
    assert momentum_sub_score(_momentum(rsi_14=60.0, return_20d=0.15)) > 0.7


def test_momentum_sub_score_overbought_penalised() -> None:
    hi = momentum_sub_score(_momentum(rsi_14=60.0))
    overb = momentum_sub_score(_momentum(rsi_14=90.0))
    assert overb < hi


def test_momentum_sub_score_negative_returns_drag() -> None:
    pos = momentum_sub_score(_momentum(return_20d=0.10))
    neg = momentum_sub_score(_momentum(return_20d=-0.10))
    assert neg < pos


# -------------------- Volume / volatility sub-scores --------------------


def test_volume_sub_score_monotonic_in_ratio() -> None:
    a = volume_sub_score(_volume(volume_ratio=0.5))
    b = volume_sub_score(_volume(volume_ratio=1.0))
    c = volume_sub_score(_volume(volume_ratio=2.0))
    assert a <= b <= c
    assert c == pytest.approx(1.0)


def test_volatility_sub_score_lower_is_better() -> None:
    low = volatility_sub_score(_volatility(atr_14=1.0), last_close=100.0)
    high = volatility_sub_score(_volatility(atr_14=5.0), last_close=100.0)
    assert low > high


# -------------------- Fundamentals --------------------


def test_fundamental_sub_score_all_missing_is_neutral() -> None:
    assert fundamental_sub_score(FundamentalFeatures()) == pytest.approx(0.5)


def test_fundamental_sub_score_cheap_vs_sector_scores_high() -> None:
    cheap = FundamentalFeatures(pe_vs_sector_median=-0.3)
    expensive = FundamentalFeatures(pe_vs_sector_median=0.3)
    assert fundamental_sub_score(cheap) > fundamental_sub_score(expensive)


# -------------------- Support/Resistance --------------------


def test_sr_sub_score_caps_at_52w_high() -> None:
    # Exactly at 52w high → should not exceed 0.75 to avoid overbought reward.
    sr = _sr(distance_to_52w_high_pct=0.0, near_52w_high=True)
    assert support_resistance_sub_score(sr) <= 0.75


# -------------------- Composite --------------------


def test_compose_score_respects_weights() -> None:
    sub = SubScores(
        moving_average=1.0, momentum=0.0, volume=0.0,
        volatility=0.0, fundamental=0.0, support_resistance=0.0,
    )
    weights = ScoringWeights.model_validate({})  # defaults
    score = compose_score(sub, weights)
    assert score == pytest.approx(weights.moving_average / weights.total())


def test_compose_score_handles_zero_weights() -> None:
    sub = SubScores(
        moving_average=1.0, momentum=1.0, volume=1.0,
        volatility=1.0, fundamental=1.0, support_resistance=1.0,
    )
    zero = ScoringWeights(
        moving_average=0, momentum=0, volume=0,
        volatility=0, fundamental=0, support_resistance=0,
    )
    assert compose_score(sub, zero) == pytest.approx(0.5)  # neutral fallback


# -------------------- Property tests --------------------


@settings(max_examples=100, deadline=None)
@given(
    rsi=st.floats(min_value=0.0, max_value=100.0),
    r5=st.floats(min_value=-0.5, max_value=0.5),
    r10=st.floats(min_value=-0.5, max_value=0.5),
    r20=st.floats(min_value=-0.5, max_value=0.5),
)
def test_momentum_sub_score_always_unit_interval(rsi: float, r5: float, r10: float, r20: float) -> None:
    s = momentum_sub_score(_momentum(rsi_14=rsi, return_5d=r5, return_10d=r10, return_20d=r20))
    assert 0.0 <= s <= 1.0


@settings(max_examples=100, deadline=None)
@given(
    ratio=st.floats(min_value=0.0, max_value=10.0),
    atr=st.floats(min_value=0.0, max_value=100.0),
    close=st.floats(min_value=1.0, max_value=10000.0),
)
def test_volume_and_volatility_unit_range(ratio: float, atr: float, close: float) -> None:
    assert 0.0 <= volume_sub_score(_volume(volume_ratio=ratio)) <= 1.0
    assert 0.0 <= volatility_sub_score(_volatility(atr_14=atr), last_close=close) <= 1.0


def test_compute_sub_scores_deterministic_on_same_input() -> None:
    features = _features()
    a = compute_sub_scores(features)
    b = compute_sub_scores(features)
    assert a == b


def test_composite_score_bounded() -> None:
    features = _features()
    sub = compute_sub_scores(features)
    weights = ScoringWeights.model_validate({})
    assert 0.0 <= compose_score(sub, weights) <= 1.0
