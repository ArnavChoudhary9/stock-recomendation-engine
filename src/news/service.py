"""NewsService — orchestrates provider → dedup → sentiment → :class:`NewsBundle`.

Caching is in-memory with TTL — personal use, no multi-process concerns.
Aggregate sentiment is a recency-weighted mean: fresher articles carry more
weight than week-old ones, up to the configured ``time_window_hours``.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import NewsConfig
from src.contracts import Article, NewsBundle, RawArticle
from src.news.dedup import dedupe_articles
from src.news.providers.base import NewsProvider, NewsProviderError
from src.news.providers.google_rss import GoogleNewsRSSProvider
from src.news.providers.newsapi import NewsAPIProvider
from src.news.sentiment.base import SentimentAnalyzer, SentimentAnalyzerError
from src.news.sentiment.textblob import TextBlobSentimentAnalyzer

log = logging.getLogger(__name__)


class NewsServiceError(Exception):
    """Surface-level failure — provider down, analyzer misconfigured, etc."""


@dataclass
class _CacheEntry:
    bundle: NewsBundle
    stored_at: float  # monotonic seconds


class NewsService:
    """Produce :class:`NewsBundle` objects for a stock, with TTL caching."""

    def __init__(
        self,
        provider: NewsProvider,
        analyzer: SentimentAnalyzer,
        config: NewsConfig,
    ) -> None:
        self.provider = provider
        self.analyzer = analyzer
        self.config = config
        self._cache: dict[tuple[str, int], _CacheEntry] = {}

    async def get_news(
        self,
        symbol: str,
        *,
        company_name: str | None = None,
        refresh: bool = False,
    ) -> NewsBundle:
        """Fetch (or return cached) news for ``symbol``. ``company_name`` improves recall."""
        sym = symbol.strip().upper()
        window_h = self.config.news.time_window_hours
        cache_key = (sym, window_h)

        if not refresh:
            cached = self._cache.get(cache_key)
            if cached and self._cache_fresh(cached):
                return cached.bundle

        query = _build_query(sym, company_name)
        now = datetime.now(UTC)
        from_date = now - timedelta(hours=window_h)

        try:
            raw = await self.provider.fetch_news(
                query, from_date, now,
                limit=self.config.news.max_articles_per_stock * 2,  # buffer for dedup losses
            )
        except NewsProviderError as e:
            log.warning("news fetch failed for %s: %s", sym, e)
            # Fall back to whatever we have cached, even if stale.
            stale = self._cache.get(cache_key)
            if stale is not None:
                return stale.bundle
            return _empty_bundle(sym, window_h)

        # Sort by ``published_at`` ascending so dedup preserves earliest timestamps.
        raw_sorted = sorted(raw, key=lambda a: a.published_at)
        deduped = dedupe_articles(
            raw_sorted,
            similarity_threshold=self.config.news.dedup_similarity_threshold,
        )
        deduped = deduped[: self.config.news.max_articles_per_stock]

        articles = self._score_articles(deduped)
        aggregate = self._aggregate_sentiment(articles, now, window_h)

        bundle = NewsBundle(
            symbol=sym,
            timestamp=now,
            articles=articles,
            aggregate_sentiment=aggregate,
            article_count=len(articles),
            time_window_hours=window_h,
        )
        self._cache[cache_key] = _CacheEntry(bundle=bundle, stored_at=time.monotonic())
        return bundle

    def _cache_fresh(self, entry: _CacheEntry) -> bool:
        ttl = self.config.news.cache_ttl_minutes * 60
        if ttl <= 0:
            return False
        return (time.monotonic() - entry.stored_at) < ttl

    def _score_articles(self, articles: list[RawArticle]) -> list[Article]:
        min_len = self.config.sentiment.min_text_length
        scored: list[Article] = []
        for article in articles:
            text = _joined_text(article)
            if len(text) < min_len:
                # Too short to reliably score — emit a neutral result.
                neutral = self.analyzer.analyze("")
                enriched = _to_enriched(article, neutral)
            else:
                try:
                    result = self.analyzer.analyze(text)
                except SentimentAnalyzerError as e:
                    log.debug("sentiment failed on '%s': %s", article.title[:40], e)
                    result = self.analyzer.analyze("")
                enriched = _to_enriched(article, result)
            scored.append(enriched)
        return scored

    def _aggregate_sentiment(
        self, articles: list[Article], as_of: datetime, window_h: int
    ) -> float:
        """Recency-weighted mean — newest article has weight ~1.0, oldest in window ~0.3.

        Articles outside the window contribute nothing. Empty → 0.0 neutral.
        """
        if not articles:
            return 0.0
        window_s = window_h * 3600
        weighted_sum = 0.0
        weight_total = 0.0
        for article in articles:
            age_s = max(0.0, (as_of - _as_utc(article.published_at)).total_seconds())
            recency = max(0.0, 1.0 - age_s / window_s)
            weight = 0.3 + 0.7 * recency  # keep a floor so older items still count
            weighted_sum += article.sentiment.score * weight
            weight_total += weight
        if weight_total == 0:
            return 0.0
        value = weighted_sum / weight_total
        return max(-1.0, min(1.0, value))


def _build_query(symbol: str, company_name: str | None) -> str:
    """Prefer company name (higher recall) over symbol (often ambiguous)."""
    if company_name:
        return f'"{company_name}" OR "{symbol}"'
    return f'"{symbol}" stock NSE'


def _joined_text(article: RawArticle) -> str:
    parts = [article.title]
    if article.summary:
        parts.append(article.summary)
    if article.content:
        parts.append(article.content)
    return " ".join(parts).strip()


def _to_enriched(article: RawArticle, sentiment: object) -> Article:
    from src.contracts import SentimentResult  # local to avoid cycle at import time

    assert isinstance(sentiment, SentimentResult)
    return Article(
        title=article.title,
        summary=article.summary,
        url=article.url,
        source=article.source,
        published_at=article.published_at,
        sentiment=sentiment,
    )


def _as_utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


def _empty_bundle(symbol: str, window_h: int) -> NewsBundle:
    return NewsBundle(
        symbol=symbol,
        timestamp=datetime.now(UTC),
        articles=[],
        aggregate_sentiment=0.0,
        article_count=0,
        time_window_hours=window_h,
    )


def build_news_service(config: NewsConfig) -> NewsService:
    """Wire up a :class:`NewsService` from config + environment.

    ``newsapi`` is selected only if ``NEWSAPI_KEY`` is set; otherwise we fall
    back to ``google_rss`` with a warning. Sentiment analyzer is picked by
    ``config.sentiment.analyzer``.
    """
    provider_name = config.news.provider.lower()
    api_key = os.environ.get("NEWSAPI_KEY", "").strip()

    if provider_name == "newsapi":
        if not api_key:
            log.warning(
                "provider=newsapi but NEWSAPI_KEY is unset — falling back to google_rss"
            )
            provider: NewsProvider = GoogleNewsRSSProvider(
                language=config.news.language,
                country=config.news.country,
                timeout_seconds=config.news.request_timeout_seconds,
                max_retries=config.news.max_retries,
                backoff_base_seconds=config.news.backoff_base_seconds,
            )
        else:
            provider = NewsAPIProvider(
                api_key=api_key,
                language=config.news.language,
                timeout_seconds=config.news.request_timeout_seconds,
                max_retries=config.news.max_retries,
                backoff_base_seconds=config.news.backoff_base_seconds,
            )
    elif provider_name == "google_rss":
        provider = GoogleNewsRSSProvider(
            language=config.news.language,
            country=config.news.country,
            timeout_seconds=config.news.request_timeout_seconds,
            max_retries=config.news.max_retries,
            backoff_base_seconds=config.news.backoff_base_seconds,
        )
    else:
        raise NewsServiceError(f"unknown news provider '{config.news.provider}'")

    analyzer_name = config.sentiment.analyzer.lower()
    if analyzer_name == "textblob":
        analyzer: SentimentAnalyzer = TextBlobSentimentAnalyzer(
            positive_threshold=config.sentiment.positive_threshold,
            negative_threshold=config.sentiment.negative_threshold,
        )
    else:
        raise NewsServiceError(
            f"sentiment analyzer '{config.sentiment.analyzer}' not yet implemented"
        )

    return NewsService(provider, analyzer, config)
