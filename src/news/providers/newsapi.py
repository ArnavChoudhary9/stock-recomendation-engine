"""NewsAPI.org provider (primary when ``NEWSAPI_KEY`` is set).

NewsAPI has a 100-req/day free tier. We hit ``/v2/everything`` with the
query, date range, and language filter. On 429 we surface a
:class:`RateLimitedError` so the retry helper can back off.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import HttpUrl, ValidationError

from src.contracts import RawArticle
from src.news.providers.base import (
    NewsProvider,
    NewsProviderError,
    RateLimitedError,
    with_backoff,
)

log = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"


class NewsAPIProvider(NewsProvider):
    """HTTP client for NewsAPI.org. Stateless — safe to share across tasks."""

    name = "newsapi"

    def __init__(
        self,
        api_key: str,
        *,
        language: str = "en",
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise NewsProviderError(
                "NewsAPI key is missing — set NEWSAPI_KEY in your environment"
            )
        self.api_key = api_key
        self.language = language
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._client = client  # injected for tests; else created per-request

    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        params: dict[str, str | int] = {
            "q": query,
            "from": _iso_utc(from_date),
            "to": _iso_utc(to_date),
            "language": self.language,
            "sortBy": "publishedAt",
            "pageSize": min(max(1, limit), 100),
        }
        headers = {"X-Api-Key": self.api_key}

        async def _do_fetch() -> dict[str, Any]:
            client_cm = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
            should_close = self._client is None
            try:
                resp = await client_cm.get(NEWSAPI_URL, params=params, headers=headers)
            finally:
                if should_close and not self._client:
                    await client_cm.aclose()

            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                raise RateLimitedError("NewsAPI rate-limited", retry_after=retry_after)
            if resp.status_code >= 400:
                raise NewsProviderError(
                    f"NewsAPI returned {resp.status_code}: {resp.text[:200]}"
                )
            payload: dict[str, Any] = resp.json()
            if payload.get("status") != "ok":
                raise NewsProviderError(
                    f"NewsAPI error: {payload.get('code')} — {payload.get('message')}"
                )
            return payload

        payload = await with_backoff(
            _do_fetch,
            max_retries=self.max_retries,
            base_seconds=self.backoff_base_seconds,
            logger=log,
        )

        articles: list[RawArticle] = []
        for item in payload.get("articles", [])[:limit]:
            parsed = _parse_article(item)
            if parsed is not None:
                articles.append(parsed)
        return articles


def _iso_utc(dt: datetime) -> str:
    """NewsAPI expects ISO-8601 in UTC. Naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_retry_after(header: str | None) -> float | None:
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def _parse_article(item: dict[str, Any]) -> RawArticle | None:
    url = item.get("url")
    title = item.get("title") or ""
    published_raw = item.get("publishedAt")
    if not url or not title or not published_raw:
        return None
    try:
        published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    except ValueError:
        log.debug("skipping article with unparseable publishedAt: %r", published_raw)
        return None
    try:
        return RawArticle(
            title=title,
            summary=item.get("description"),
            content=item.get("content"),
            url=HttpUrl(url),
            source=(item.get("source") or {}).get("name", "unknown"),
            published_at=published,
            language=item.get("language") or "en",
        )
    except ValidationError as e:
        log.debug("skipping article failing validation: %s", e)
        return None
