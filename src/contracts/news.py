"""News layer contracts: raw articles, sentiment results, news bundles."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SentimentLabel = Literal["positive", "negative", "neutral"]


class RawArticle(BaseModel):
    """Article as returned by a NewsProvider, before sentiment scoring."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1)
    summary: str | None = None
    content: str | None = None
    url: HttpUrl
    source: str
    published_at: datetime
    language: str | None = "en"


class SentimentResult(BaseModel):
    """Output of a SentimentAnalyzer for a single piece of text."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=-1, le=1, description="-1 = very negative, +1 = very positive")
    label: SentimentLabel
    confidence: float = Field(..., ge=0, le=1)
    analyzer: str = Field(..., description="Identifier of analyzer used, e.g. 'textblob'")


class Article(BaseModel):
    """Article enriched with sentiment, ready to attach to a NewsBundle."""

    model_config = ConfigDict(frozen=True)

    title: str
    summary: str | None = None
    url: HttpUrl
    source: str
    published_at: datetime
    sentiment: SentimentResult


class NewsBundle(BaseModel):
    """All recent news for a stock with aggregate sentiment."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    articles: list[Article] = Field(default_factory=list)
    aggregate_sentiment: float = Field(..., ge=-1, le=1)
    article_count: int = Field(..., ge=0)
    time_window_hours: int = Field(..., gt=0)

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
