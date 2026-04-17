"""NewsProvider abstract interface + shared retry helper.

Every provider returns :class:`RawArticle` lists — the service layer handles
dedup, sentiment, and packaging into :class:`NewsBundle`. Providers should
normalise upstream quirks here (e.g. timezone handling, missing summaries).
"""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TypeVar

from src.contracts import RawArticle

log = logging.getLogger(__name__)

T = TypeVar("T")


class NewsProviderError(Exception):
    """Base class for news-provider failures."""


class RateLimitedError(NewsProviderError):
    """Upstream throttled the request. ``retry_after`` hints at seconds to wait."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NewsProvider(ABC):
    """Contract for news-fetching backends."""

    name: str

    @abstractmethod
    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        """Return up to ``limit`` articles matching ``query`` in ``[from_date, to_date]``.

        Dates are UTC-naive acceptable; implementations should interpret them as UTC.
        """


async def with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    base_seconds: float,
    logger: logging.Logger | None = None,
) -> T:
    """Run ``fn`` with exponential backoff on :class:`RateLimitedError`.

    Waits ``base * 2^attempt`` (plus a small jitter) between retries. Any
    ``retry_after`` hint from the exception overrides that delay.
    """
    log_ = logger or log
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except RateLimitedError as e:
            last_exc = e
            if attempt == max_retries:
                break
            wait = e.retry_after if e.retry_after is not None else base_seconds * (2**attempt)
            jitter = random.uniform(0, base_seconds * 0.5)
            log_.warning(
                "rate-limited (attempt %d/%d) — sleeping %.1fs",
                attempt + 1, max_retries, wait + jitter,
            )
            await asyncio.sleep(wait + jitter)
    assert last_exc is not None  # max_retries=0 with a failure still falls through here
    raise last_exc
