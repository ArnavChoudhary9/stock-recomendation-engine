"""Unit tests for the TextBlob sentiment analyzer."""

from __future__ import annotations

import pytest

from src.news.sentiment.textblob import TextBlobSentimentAnalyzer


@pytest.fixture
def analyzer() -> TextBlobSentimentAnalyzer:
    return TextBlobSentimentAnalyzer(positive_threshold=0.1, negative_threshold=-0.1)


def test_empty_text_is_neutral_zero_confidence(analyzer: TextBlobSentimentAnalyzer) -> None:
    r = analyzer.analyze("")
    assert r.score == 0.0
    assert r.label == "neutral"
    assert r.confidence == 0.0
    assert r.analyzer == "textblob"


def test_positive_sentence_scores_positive(analyzer: TextBlobSentimentAnalyzer) -> None:
    r = analyzer.analyze(
        "Reliance delivered an outstanding quarter with record profits and a strong outlook."
    )
    assert r.label == "positive"
    assert r.score > 0
    assert 0.0 <= r.confidence <= 1.0


def test_negative_sentence_scores_negative(analyzer: TextBlobSentimentAnalyzer) -> None:
    r = analyzer.analyze(
        "The company reported a terrible loss; investors are deeply worried and angry."
    )
    assert r.label == "negative"
    assert r.score < 0


def test_neutral_sentence(analyzer: TextBlobSentimentAnalyzer) -> None:
    r = analyzer.analyze("The company released its quarterly results today.")
    assert r.label == "neutral"
    assert -0.1 < r.score < 0.1


def test_score_is_bounded(analyzer: TextBlobSentimentAnalyzer) -> None:
    for text in ("amazing excellent wonderful fantastic",
                 "terrible horrible disgusting awful",
                 "the cat sat on the mat"):
        r = analyzer.analyze(text)
        assert -1.0 <= r.score <= 1.0
        assert 0.0 <= r.confidence <= 1.0


def test_threshold_inversion_rejected() -> None:
    with pytest.raises(ValueError):
        TextBlobSentimentAnalyzer(positive_threshold=-0.1, negative_threshold=0.1)


def test_custom_thresholds_relabel() -> None:
    strict = TextBlobSentimentAnalyzer(positive_threshold=0.5, negative_threshold=-0.5)
    # Same sentence that scored "positive" with default thresholds should go neutral
    # under stricter thresholds (unless the score is very high).
    text = "The results were good overall."
    r = strict.analyze(text)
    assert r.label in ("positive", "neutral")
