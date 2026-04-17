"""News providers. Implementations live behind :class:`NewsProvider`."""

from src.news.providers.base import (
    NewsProvider,
    NewsProviderError,
    RateLimitedError,
    with_backoff,
)
from src.news.providers.google_rss import GoogleNewsRSSProvider
from src.news.providers.newsapi import NewsAPIProvider

__all__ = [
    "GoogleNewsRSSProvider",
    "NewsAPIProvider",
    "NewsProvider",
    "NewsProviderError",
    "RateLimitedError",
    "with_backoff",
]
