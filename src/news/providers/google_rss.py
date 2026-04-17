"""Google News RSS fallback provider — no API key required.

The Google News search RSS endpoint accepts a free-text query and returns
an Atom-ish feed. We parse it with ``feedparser``, which handles the quirks
of missing/mangled timestamps. Results are trimmed to ``[from_date, to_date]``
because Google's ``when:<period>`` query param isn't consistently respected.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

import feedparser
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

GOOGLE_NEWS_URL = "https://news.google.com/rss/search"


class GoogleNewsRSSProvider(NewsProvider):
    """Parses Google News search RSS feeds. Respects the ``when:`` query hint."""

    name = "google_rss"

    def __init__(
        self,
        *,
        language: str = "en",
        country: str = "IN",
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.language = language
        self.country = country
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._client = client

    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        window_hours = max(
            1, int((to_date - from_date).total_seconds() // 3600)
        )
        # ``when:24h`` biases Google toward recency. We still filter client-side.
        q = f"{query} when:{window_hours}h"
        url = (
            f"{GOOGLE_NEWS_URL}?q={quote_plus(q)}"
            f"&hl={self.language}&gl={self.country}"
            f"&ceid={self.country}:{self.language}"
        )

        async def _do_fetch() -> str:
            # Google News RSS responds with a 302 to the regional host; follow it.
            client_cm = self._client or httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            )
            should_close = self._client is None
            try:
                resp = await client_cm.get(url)
            finally:
                if should_close and not self._client:
                    await client_cm.aclose()
            if resp.status_code == 429:
                raise RateLimitedError("Google News rate-limited")
            if resp.status_code >= 400:
                raise NewsProviderError(
                    f"Google News RSS returned {resp.status_code}"
                )
            return resp.text

        xml = await with_backoff(
            _do_fetch,
            max_retries=self.max_retries,
            base_seconds=self.backoff_base_seconds,
            logger=log,
        )

        # feedparser is CPU-bound; offload to thread to keep the loop unblocked.
        feed = await asyncio.to_thread(feedparser.parse, xml)
        articles: list[RawArticle] = []
        for entry in feed.entries[: limit * 2]:  # over-fetch, we'll filter by date
            parsed = _parse_entry(entry, self.language)
            if parsed is None:
                continue
            if parsed.published_at < from_date or parsed.published_at > to_date:
                continue
            articles.append(parsed)
            if len(articles) >= limit:
                break
        return articles


def _parse_entry(entry: Any, default_language: str) -> RawArticle | None:
    title = getattr(entry, "title", None)
    link = getattr(entry, "link", None)
    if not title or not link:
        return None

    published = _parse_entry_datetime(entry)
    if published is None:
        return None

    source_name = "google_news"
    source_obj = getattr(entry, "source", None)
    if source_obj is not None:
        candidate: Any = getattr(source_obj, "title", None)
        if candidate is None and isinstance(source_obj, dict):
            candidate = source_obj.get("title")
        if isinstance(candidate, str) and candidate:
            source_name = candidate

    try:
        return RawArticle(
            title=title,
            summary=getattr(entry, "summary", None),
            content=None,
            url=HttpUrl(link),
            source=source_name,
            published_at=published,
            language=default_language,
        )
    except ValidationError as e:
        log.debug("skipping RSS entry failing validation: %s", e)
        return None


def _parse_entry_datetime(entry: Any) -> datetime | None:
    """feedparser exposes ``published_parsed`` as a time.struct_time in UTC."""
    parsed = getattr(entry, "published_parsed", None)
    if parsed is None:
        raw = getattr(entry, "published", None)
        if not raw:
            return None
        try:
            # Fallback: attempt ISO parse.
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    try:
        y, mo, d, h, mi, s = parsed[:6]
        return datetime(y, mo, d, h, mi, s, tzinfo=UTC)
    except (TypeError, ValueError):
        return None
