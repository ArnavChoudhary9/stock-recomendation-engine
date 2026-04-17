"""Phase 3 — news fetching, dedup, sentiment, bundled output."""

from src.news.dedup import dedupe_articles
from src.news.providers import (
    GoogleNewsRSSProvider,
    NewsAPIProvider,
    NewsProvider,
    NewsProviderError,
    RateLimitedError,
)
from src.news.sentiment import (
    SentimentAnalyzer,
    SentimentAnalyzerError,
    TextBlobSentimentAnalyzer,
)
from src.news.service import NewsService, NewsServiceError, build_news_service

__all__ = [
    "GoogleNewsRSSProvider",
    "NewsAPIProvider",
    "NewsProvider",
    "NewsProviderError",
    "NewsService",
    "NewsServiceError",
    "RateLimitedError",
    "SentimentAnalyzer",
    "SentimentAnalyzerError",
    "TextBlobSentimentAnalyzer",
    "build_news_service",
    "dedupe_articles",
]
