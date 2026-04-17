"""Unit tests for the deterministic BUY/HOLD/SELL mapper in processing.scoring."""

from __future__ import annotations

from src.contracts import FundamentalFeatures, SubScores
from src.processing.scoring import derive_recommendation


def _subs(
    ma: float = 0.5,
    momentum: float = 0.5,
    volume: float = 0.5,
    volatility: float = 0.5,
    fundamental: float = 0.5,
    support_resistance: float = 0.5,
) -> SubScores:
    return SubScores(
        moving_average=ma,
        momentum=momentum,
        volume=volume,
        volatility=volatility,
        fundamental=fundamental,
        support_resistance=support_resistance,
    )


def _funds(pe_vs_sector: float | None = None) -> FundamentalFeatures:
    return FundamentalFeatures(pe_vs_sector_median=pe_vs_sector)


def test_high_score_maps_to_buy() -> None:
    rec, rationale = derive_recommendation(
        score=0.80,
        sub_scores=_subs(fundamental=0.75),
        fundamentals=_funds(pe_vs_sector=-0.1),
        signals={"golden_cross": True, "ma_bullish_stack": True},
    )
    assert rec == "BUY"
    assert "composite" in rationale
    assert "cheap" in rationale


def test_low_score_maps_to_sell() -> None:
    rec, _ = derive_recommendation(
        score=0.25,
        sub_scores=_subs(fundamental=0.25),
        fundamentals=_funds(),
        signals={"death_cross": True, "ma_bearish_stack": True},
    )
    assert rec == "SELL"


def test_mid_score_stays_hold() -> None:
    rec, _ = derive_recommendation(
        score=0.50,
        sub_scores=_subs(fundamental=0.50),
        fundamentals=_funds(),
        signals={},
    )
    assert rec == "HOLD"


def test_death_cross_caps_buy_to_hold() -> None:
    rec, rationale = derive_recommendation(
        score=0.70,
        sub_scores=_subs(fundamental=0.60),
        fundamentals=_funds(),
        signals={"death_cross": True},
    )
    assert rec == "HOLD"
    assert "death cross" in rationale


def test_overbought_caps_buy_to_hold() -> None:
    rec, _ = derive_recommendation(
        score=0.72,
        sub_scores=_subs(fundamental=0.60),
        fundamentals=_funds(),
        signals={"overbought": True},
    )
    assert rec == "HOLD"


def test_strong_fundamentals_upgrade_hold_to_buy() -> None:
    rec, _ = derive_recommendation(
        score=0.55,  # inside HOLD band
        sub_scores=_subs(fundamental=0.85),  # strong
        fundamentals=_funds(pe_vs_sector=-0.2),
        signals={},
    )
    assert rec == "BUY"


def test_weak_fundamentals_downgrade_hold_to_sell() -> None:
    rec, _ = derive_recommendation(
        score=0.45,  # inside HOLD band
        sub_scores=_subs(fundamental=0.20),  # weak
        fundamentals=_funds(pe_vs_sector=0.3),
        signals={},
    )
    assert rec == "SELL"


def test_golden_cross_blocks_weak_fundamentals_downgrade() -> None:
    """A fresh golden cross should not be downgraded to SELL even with weak fundamentals."""
    rec, _ = derive_recommendation(
        score=0.45,
        sub_scores=_subs(fundamental=0.20),
        fundamentals=_funds(),
        signals={"golden_cross": True},
    )
    assert rec == "HOLD"
