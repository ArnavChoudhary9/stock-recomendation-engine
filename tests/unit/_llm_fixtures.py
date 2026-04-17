"""Shared test helpers for Phase 4 (LLM) unit tests.

Builds minimal valid ``StockAnalysis`` and ``NewsBundle`` instances without
depending on fixtures from Phase 2 or Phase 3, so these tests stay independent
while other phases are under active development.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import TypeAdapter
from pydantic.networks import HttpUrl

from src.contracts import (
    AnalysisMetadata,
    Article,
    Features,
    FundamentalFeatures,
    Momentum,
    MovingAverages,
    NewsBundle,
    SentimentResult,
    StockAnalysis,
    SubScores,
    SupportResistance,
    Volatility,
    VolumeFeatures,
)

_URL = TypeAdapter(HttpUrl)


def make_analysis(symbol: str = "RELIANCE", score: float = 0.72) -> StockAnalysis:
    now = datetime.now(UTC)
    mas = MovingAverages(
        sma_20=2950.0,
        sma_50=2880.0,
        sma_200=2700.0,
        ema_12=2970.0,
        ema_26=2930.0,
        price_to_sma20_pct=1.5,
        price_to_sma50_pct=3.8,
        price_to_sma200_pct=10.9,
        alignment="bullish",
        sma50_slope="rising",
        sma200_slope="rising",
        crossover="golden_cross",
        crossover_days_ago=3,
    )
    features = Features(
        symbol=symbol,
        as_of=now,
        last_close=2995.0,
        moving_averages=mas,
        momentum=Momentum(rsi_14=62.4, return_5d=0.018, return_10d=0.032, return_20d=0.057),
        volume=VolumeFeatures(
            current_volume=9_500_000,
            avg_volume_20d=6_200_000.0,
            volume_ratio=1.53,
            obv=1.25e9,
        ),
        volatility=Volatility(atr_14=42.3, std_dev_20=38.6),
        fundamentals=FundamentalFeatures(
            pe=24.1,
            pe_vs_sector_median=-0.08,
            market_cap=2_050_000_000_000.0,
            market_cap_tier="large",
            roe=0.14,
            roe_sector_rank=0.72,
        ),
        support_resistance=SupportResistance(
            high_52w=3100.0,
            low_52w=2300.0,
            distance_to_52w_high_pct=-3.4,
            distance_to_52w_low_pct=30.2,
            near_52w_high=False,
            near_52w_low=False,
        ),
    )
    sub = SubScores(
        moving_average=0.82,
        momentum=0.71,
        volume=0.66,
        volatility=0.55,
        fundamental=0.74,
        support_resistance=0.60,
    )
    meta = AnalysisMetadata(
        config_hash="testhash123",
        scoring_version="0.1.0",
        computed_at=now,
        data_points_used=260,
        warnings=[],
    )
    return StockAnalysis(
        symbol=symbol,
        timestamp=now,
        moving_averages=mas,
        features=features,
        score=score,
        sub_scores=sub,
        signals={
            "golden_cross": True,
            "ma_bullish_stack": True,
            "momentum_strong": True,
            "overbought": False,
            "volume_spike": False,
            "near_52w_high": False,
        },
        metadata=meta,
    )


def make_news(symbol: str = "RELIANCE", count: int = 3) -> NewsBundle:
    now = datetime.now(UTC)
    articles = [
        Article(
            title=f"{symbol} reports strong quarterly results #{i}",
            summary="Growth driven by retail and digital segments.",
            url=_URL.validate_python(f"https://example.com/{symbol.lower()}/{i}"),
            source="ExampleWire",
            published_at=now - timedelta(hours=i + 1),
            sentiment=SentimentResult(
                score=0.4 if i % 2 == 0 else -0.1,
                label="positive" if i % 2 == 0 else "neutral",
                confidence=0.8,
                analyzer="textblob",
            ),
        )
        for i in range(count)
    ]
    return NewsBundle(
        symbol=symbol,
        timestamp=now,
        articles=articles,
        aggregate_sentiment=0.22,
        article_count=len(articles),
        time_window_hours=72,
    )


VALID_LLM_JSON = """
{
  "symbol": "IGNORED",
  "timestamp": "2020-01-01T00:00:00+00:00",
  "summary": "RELIANCE is in a bullish MA configuration with a recent golden cross and strong momentum.",
  "insights": [
    "Golden cross 3 days ago confirms the bullish alignment.",
    "Volume ratio of 1.53x supports the current up-move.",
    "ROE at the 72nd sector percentile strengthens fundamentals."
  ],
  "risks": [
    "RSI nearing elevated range reduces room for further expansion.",
    "Distance from SMA(200) at +10.9% leaves the stock stretched long-term."
  ],
  "news_impact": "Positive tone in recent coverage reinforces the quantitative signal.",
  "confidence": 0.78,
  "reasoning_chain": [
    "Score 0.72 reflects strong MA + momentum contributions.",
    "News sentiment +0.22 is mildly supportive.",
    "No bearish signals counterbalance the stack."
  ],
  "recommendation": "BUY",
  "recommendation_rationale": "Bullish MA stack plus supportive news aligns with the deterministic BUY call.",
  "sources": []
}
"""
