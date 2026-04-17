"""TextBlob-based sentiment analyzer.

TextBlob gives polarity in ``[-1, +1]`` and subjectivity in ``[0, 1]``.
We map polarity directly to ``score`` and derive a discrete label from
configurable thresholds. Subjectivity is used as a rough confidence proxy
(objective prose → lower confidence in the polarity estimate).
"""

from __future__ import annotations

import logging
from typing import Any, cast

from src.contracts import SentimentLabel, SentimentResult
from src.news.sentiment.base import SentimentAnalyzer, SentimentAnalyzerError

log = logging.getLogger(__name__)


class TextBlobSentimentAnalyzer(SentimentAnalyzer):
    """Stateless wrapper around ``textblob.TextBlob``."""

    name = "textblob"

    def __init__(
        self,
        *,
        positive_threshold: float = 0.1,
        negative_threshold: float = -0.1,
    ) -> None:
        if positive_threshold <= negative_threshold:
            raise ValueError(
                f"positive_threshold ({positive_threshold}) must exceed "
                f"negative_threshold ({negative_threshold})"
            )
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold

    def analyze(self, text: str) -> SentimentResult:
        stripped = text.strip()
        if not stripped:
            return SentimentResult(score=0.0, label="neutral", confidence=0.0, analyzer=self.name)

        try:
            # Import lazily so the dependency is only required when this analyzer is used.
            from textblob import TextBlob
        except ImportError as e:
            raise SentimentAnalyzerError(
                "textblob is not installed — add it to your deps or switch analyzer"
            ) from e

        try:
            # TextBlob exposes `sentiment` via @cached_property returning a
            # Sentiment(polarity, subjectivity) named tuple — static checkers see
            # only the descriptor, so route through `Any` to get real access.
            sentiment = cast(Any, TextBlob(stripped)).sentiment
            polarity = float(sentiment[0])
            subjectivity = float(sentiment[1])
        except Exception as e:
            raise SentimentAnalyzerError(f"TextBlob failed on input: {e}") from e

        polarity = _clamp(polarity, -1.0, 1.0)
        subjectivity = _clamp(subjectivity, 0.0, 1.0)

        label: SentimentLabel
        if polarity >= self.positive_threshold:
            label = "positive"
        elif polarity <= self.negative_threshold:
            label = "negative"
        else:
            label = "neutral"

        # Confidence: how strongly the polarity departs from neutral, reduced by
        # how subjective the text is. Fully objective + extreme polarity → ~1.0.
        confidence = _clamp(abs(polarity) * (1.0 - 0.5 * subjectivity), 0.0, 1.0)
        return SentimentResult(
            score=polarity, label=label, confidence=confidence, analyzer=self.name
        )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
