"""SentimentAnalyzer abstract interface.

Analyzer converts free-form article text into a :class:`SentimentResult`
bounded to [-1, 1]. Implementations should be stateless so they can be
shared across concurrent requests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.contracts import SentimentResult


class SentimentAnalyzerError(Exception):
    """Raised when analysis cannot complete (bad input, missing model, etc.)."""


class SentimentAnalyzer(ABC):
    """Contract for text-to-sentiment scoring."""

    name: str

    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        """Return a sentiment score + label for ``text``.

        Implementations must return a neutral result for very short text
        rather than raise — callers filter on ``min_text_length`` upstream.
        """
