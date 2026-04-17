"""LLM layer contracts: structured stock reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from src.contracts.processing import Recommendation


class NewsReference(BaseModel):
    """Compact reference to a news article cited by the LLM report.

    Embedded in :class:`StockReport` so API consumers receive the article
    links and sentiment context alongside the narrative in one payload.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    url: HttpUrl
    source: str
    published_at: datetime
    sentiment_score: float = Field(..., ge=-1, le=1)
    sentiment_label: str = Field(..., description="positive | negative | neutral")


class StockReport(BaseModel):
    """Structured LLM-generated insight that explains the quantitative analysis.

    The LLM is an enhancement, not a decision-maker — this report never modifies
    the quantitative score. It does add its *own* BUY/HOLD/SELL view based on
    news + context, which callers can compare against the deterministic
    recommendation on :class:`StockAnalysis`.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    summary: str = Field(..., description="2-3 sentence overview")
    insights: list[str] = Field(default_factory=list, max_length=5, description="Bullish factors")
    risks: list[str] = Field(default_factory=list, max_length=5, description="Risk factors")
    news_impact: str = Field(..., description="How recent news affects the outlook")
    confidence: float = Field(..., ge=0, le=1, description="LLM self-assessed confidence")
    reasoning_chain: list[str] = Field(default_factory=list, description="Step-by-step reasoning")
    recommendation: Recommendation = Field(
        default="HOLD",
        description="LLM's own BUY/HOLD/SELL view weighing news, momentum, and quantitative signals",
    )
    recommendation_rationale: str = Field(
        default="",
        description="One to two sentences explaining the LLM recommendation",
    )
    sources: list[NewsReference] = Field(
        default_factory=list,
        description="Article references (title, url, source, sentiment) backing the report",
    )
    model_used: str | None = Field(None, description="OpenRouter model id that produced report")
    degraded: bool = Field(False, description="True when all LLM providers failed and we fell back")

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
