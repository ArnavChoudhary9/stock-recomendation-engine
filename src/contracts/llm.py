"""LLM layer contracts: structured stock reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockReport(BaseModel):
    """Structured LLM-generated insight that explains the quantitative analysis.

    The LLM is an enhancement, not a decision-maker — this report never modifies
    scores or signals; it only narrates them.
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
    model_used: str | None = Field(None, description="OpenRouter model id that produced report")
    degraded: bool = Field(False, description="True when all LLM providers failed and we fell back")

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
