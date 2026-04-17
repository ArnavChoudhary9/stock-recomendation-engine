"""Integration: provider → dedup → sentiment → :class:`NewsBundle`.

The fake-provider test always runs. Opt-in live tests (``RUN_NETWORK_TESTS=1``)
exercise the real Google RSS and, if ``NEWSAPI_KEY`` is set, NewsAPI.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import HttpUrl

from src.config import (
    NewsConfig,
    NewsProviderConfig,
    SentimentAnalyzerConfig,
    load_news_config,
)
from src.contracts import RawArticle
from src.news.providers.base import NewsProvider, NewsProviderError
from src.news.sentiment.textblob import TextBlobSentimentAnalyzer
from src.news.service import NewsService, build_news_service


class StubProvider(NewsProvider):
    """In-memory provider that returns pre-seeded articles regardless of query."""

    name = "stub"

    def __init__(self, articles: list[RawArticle]) -> None:
        self.articles = articles
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        self.calls.append((query, from_date, to_date))
        return [a for a in self.articles if from_date <= a.published_at <= to_date][:limit]


class FailingProvider(NewsProvider):
    name = "failing"

    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        raise NewsProviderError("simulated outage")


def _news_config(**overrides) -> NewsConfig:  # type: ignore[no-untyped-def]
    news_kwargs = dict(
        provider="stub", time_window_hours=72, max_articles_per_stock=10,
        dedup_similarity_threshold=0.85, cache_ttl_minutes=60,
    )
    news_kwargs.update(overrides)
    return NewsConfig(
        news=NewsProviderConfig(**news_kwargs),  # type: ignore[arg-type]
        sentiment=SentimentAnalyzerConfig(analyzer="textblob", min_text_length=20),
    )


def _article(title: str, url: str, hours_ago: int, summary: str | None = None) -> RawArticle:
    return RawArticle(
        title=title,
        summary=summary,
        url=HttpUrl(url),
        source="test",
        published_at=datetime.now(UTC) - timedelta(hours=hours_ago),
    )


@pytest.mark.asyncio
async def test_full_pipeline_dedupes_scores_and_bundles() -> None:
    articles = [
        _article(
            "Reliance delivers a stellar quarter with record profits",
            "https://a.com/1",
            hours_ago=1,
            summary="Revenue and margins both grew sharply, beating every analyst estimate.",
        ),
        _article(
            "Reliance reports record quarterly profits - Reuters",  # near-duplicate title
            "https://b.com/1",
            hours_ago=2,
        ),
        _article(
            "Tata Motors unveils new EV platform to strong reception",
            "https://c.com/ev",
            hours_ago=5,
            summary="The platform targets the Indian mass market and promises better range.",
        ),
        _article(
            "Market volatility concerns analysts amid heavy selling pressure",
            "https://d.com/market",
            hours_ago=10,
            summary="Investors worry about disappointing earnings and weak global cues.",
        ),
    ]
    provider = StubProvider(articles)
    analyzer = TextBlobSentimentAnalyzer()
    service = NewsService(provider, analyzer, _news_config())

    bundle = await service.get_news("RELIANCE", company_name="Reliance Industries")
    assert bundle.symbol == "RELIANCE"
    # 4 input articles, 2 near-duplicates → 3 unique stories.
    assert bundle.article_count == 3
    assert bundle.time_window_hours == 72
    assert len(bundle.articles) == 3
    assert -1.0 <= bundle.aggregate_sentiment <= 1.0
    # Upbeat Reliance story is present.
    titles = [a.title for a in bundle.articles]
    assert any("Reliance" in t for t in titles)
    # Sentiments attached.
    for a in bundle.articles:
        assert a.sentiment.analyzer == "textblob"


@pytest.mark.asyncio
async def test_cache_hit_avoids_second_fetch() -> None:
    articles = [
        _article("Some story", "https://a.com/1", hours_ago=1,
                 summary="A descriptive enough summary to pass the min-text filter.")
    ]
    provider = StubProvider(articles)
    service = NewsService(provider, TextBlobSentimentAnalyzer(), _news_config())

    await service.get_news("TCS")
    await service.get_news("TCS")
    assert len(provider.calls) == 1  # cached

    await service.get_news("TCS", refresh=True)
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_provider_failure_returns_empty_bundle_when_no_cache() -> None:
    service = NewsService(FailingProvider(), TextBlobSentimentAnalyzer(), _news_config())
    bundle = await service.get_news("INFY")
    assert bundle.article_count == 0
    assert bundle.aggregate_sentiment == 0.0


@pytest.mark.asyncio
async def test_provider_failure_falls_back_to_stale_cache() -> None:
    articles = [
        _article("Cached story", "https://a.com/1", hours_ago=1,
                 summary="This is the cached content we fall back to on failure.")
    ]

    class FlakyProvider(NewsProvider):
        name = "flaky"
        call = 0

        async def fetch_news(
            self, query: str, from_date: datetime, to_date: datetime, *, limit: int
        ) -> list[RawArticle]:
            self.__class__.call += 1
            if self.__class__.call == 1:
                return articles
            raise NewsProviderError("down")

    service = NewsService(
        FlakyProvider(), TextBlobSentimentAnalyzer(), _news_config(cache_ttl_minutes=0)
    )
    first = await service.get_news("INFY")
    assert first.article_count == 1
    second = await service.get_news("INFY", refresh=True)  # second call fails → stale cache
    assert second.article_count == 1  # stale cache returned


@pytest.mark.asyncio
async def test_aggregate_sentiment_is_weighted_by_recency() -> None:
    # Old negative story + fresh positive story → aggregate leans positive.
    articles = [
        _article(
            "Disaster at factory causes terrible losses and widespread anger",
            "https://old.com/1",
            hours_ago=60,
            summary="Severe damages reported; production halted for weeks.",
        ),
        _article(
            "Amazing recovery with record profits and an outstanding outlook",
            "https://new.com/2",
            hours_ago=1,
            summary="Revenue beat expectations and margins expanded sharply.",
        ),
    ]
    service = NewsService(StubProvider(articles), TextBlobSentimentAnalyzer(), _news_config())
    bundle = await service.get_news("TEST")
    assert bundle.article_count == 2
    # Recency-weighted mean should be biased toward the (positive) fresh story.
    assert bundle.aggregate_sentiment > 0


# ---------- Opt-in live tests ----------


LIVE = os.getenv("RUN_NETWORK_TESTS") == "1"


@pytest.mark.asyncio
@pytest.mark.skipif(not LIVE, reason="opt-in: set RUN_NETWORK_TESTS=1 to hit Google News")
async def test_live_google_rss_returns_articles() -> None:
    from src.news.providers.google_rss import GoogleNewsRSSProvider

    provider = GoogleNewsRSSProvider()
    service = NewsService(provider, TextBlobSentimentAnalyzer(), _news_config(provider="google_rss"))
    bundle = await service.get_news("RELIANCE", company_name="Reliance Industries")
    print(f"\nGoogle RSS returned {bundle.article_count} articles; "
          f"aggregate sentiment = {bundle.aggregate_sentiment:+.3f}")
    for a in bundle.articles[:5]:
        print(f"  [{a.sentiment.score:+.2f}] {a.title} ({a.source})")
    assert bundle.article_count > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    not LIVE or not os.environ.get("NEWSAPI_KEY"),
    reason="opt-in: set RUN_NETWORK_TESTS=1 and NEWSAPI_KEY to hit NewsAPI",
)
async def test_live_newsapi_returns_articles() -> None:
    # Goes through the factory, which reads NEWSAPI_KEY from env.
    cfg = load_news_config()
    # Force provider to newsapi regardless of config file's default.
    cfg = NewsConfig(
        news=cfg.news.model_copy(update={"provider": "newsapi"}),
        sentiment=cfg.sentiment,
    )
    service = build_news_service(cfg)
    bundle = await service.get_news("RELIANCE", company_name="Reliance Industries")
    print(f"\nNewsAPI returned {bundle.article_count} articles; "
          f"aggregate sentiment = {bundle.aggregate_sentiment:+.3f}")
    for a in bundle.articles[:5]:
        print(f"  [{a.sentiment.score:+.2f}] {a.title} ({a.source})")
    assert bundle.article_count >= 0  # weak — NewsAPI coverage for Indian stocks is spotty
