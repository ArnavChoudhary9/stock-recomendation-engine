"""Article deduplication.

News wires propagate the same story across many hosts with near-identical
headlines. We drop duplicates in two passes:

1. **Exact URL** (after canonicalising query strings and trailing slashes).
2. **Fuzzy title** using ``rapidfuzz.token_set_ratio`` — tolerant to word
   reordering and trailing "| Reuters" suffixes.

Keeps the earliest ``published_at`` when duplicates collide so the oldest
known timestamp wins.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from rapidfuzz import fuzz

from src.contracts import RawArticle

_TITLE_TAIL = re.compile(r"\s*[-|–—]\s*[^-|–—]+$")  # noqa: RUF001 — real publisher separators
_WHITESPACE = re.compile(r"\s+")


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    # Drop query + fragment, normalise scheme/host case, strip trailing slash.
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", "")
    )


def _normalise_title(title: str) -> str:
    # Strip common " - Publisher" suffix, collapse whitespace, lowercase.
    stripped = _TITLE_TAIL.sub("", title).strip()
    return _WHITESPACE.sub(" ", stripped).lower()


def dedupe_articles(
    articles: list[RawArticle], *, similarity_threshold: float = 0.85
) -> list[RawArticle]:
    """Return a new list with exact-URL and fuzzy-title duplicates removed.

    Input order determines precedence — the first occurrence wins. Pass
    articles sorted by ``published_at`` ascending if you want the oldest kept.
    """
    if not articles:
        return []
    threshold_pct = max(0.0, min(1.0, similarity_threshold)) * 100.0

    seen_urls: set[str] = set()
    kept: list[RawArticle] = []
    kept_titles: list[str] = []

    for article in articles:
        canon = _canonical_url(str(article.url))
        if canon in seen_urls:
            continue
        norm_title = _normalise_title(article.title)
        if any(
            fuzz.token_set_ratio(norm_title, existing) >= threshold_pct
            for existing in kept_titles
        ):
            continue
        seen_urls.add(canon)
        kept.append(article)
        kept_titles.append(norm_title)
    return kept
