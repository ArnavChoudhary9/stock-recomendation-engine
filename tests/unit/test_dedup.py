"""Unit tests for article deduplication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import HttpUrl

from src.contracts import RawArticle
from src.news.dedup import dedupe_articles


def _article(title: str, url: str, hours_ago: int = 0) -> RawArticle:
    return RawArticle(
        title=title,
        url=HttpUrl(url),
        source="test",
        published_at=datetime.now(UTC) - timedelta(hours=hours_ago),
    )


def test_dedup_exact_url_wins_first() -> None:
    a = _article("Reliance Q3 beats", "https://example.com/news/1", hours_ago=10)
    b = _article("Different title", "https://example.com/news/1", hours_ago=5)
    result = dedupe_articles([a, b])
    assert len(result) == 1
    assert result[0] is a


def test_dedup_url_normalisation_drops_trailing_slash_and_query() -> None:
    a = _article("Reliance Q3", "https://example.com/news/1")
    b = _article("Other", "https://example.com/news/1/?utm_source=x")
    assert len(dedupe_articles([a, b])) == 1


def test_dedup_url_case_insensitive_host() -> None:
    a = _article("Reliance Q3", "https://Example.com/news/1")
    b = _article("Different", "https://example.com/news/1")
    assert len(dedupe_articles([a, b])) == 1


def test_dedup_fuzzy_title_match() -> None:
    a = _article(
        "Reliance Industries Q3 profit beats estimates",
        "https://a.com/story",
    )
    b = _article(
        "Reliance Industries beats Q3 profit estimates - Reuters",
        "https://b.com/story",
    )
    result = dedupe_articles([a, b], similarity_threshold=0.85)
    assert len(result) == 1
    assert result[0] is a


def test_dedup_distinct_stories_kept() -> None:
    a = _article("Reliance Q3 profit beats estimates", "https://a.com/1")
    b = _article("Tata Motors unveils new EV platform", "https://b.com/2")
    c = _article("HDFC Bank flags NPA rise", "https://c.com/3")
    assert len(dedupe_articles([a, b, c])) == 3


def test_dedup_threshold_boundary() -> None:
    # Similar enough to pass a loose threshold but fail a strict one.
    a = _article("Infosys wins 500M IT deal", "https://a.com/1")
    b = _article("Infosys bags 500M contract from US client", "https://b.com/2")
    strict = dedupe_articles([a, b], similarity_threshold=0.95)
    loose = dedupe_articles([a, b], similarity_threshold=0.4)
    assert len(strict) == 2
    assert len(loose) == 1


def test_dedup_empty_input_returns_empty() -> None:
    assert dedupe_articles([]) == []


def test_dedup_preserves_input_order() -> None:
    a = _article("First story", "https://a.com/1")
    b = _article("Second story", "https://b.com/2")
    c = _article("Third story", "https://c.com/3")
    result = dedupe_articles([a, b, c])
    assert [r.title for r in result] == ["First story", "Second story", "Third story"]
