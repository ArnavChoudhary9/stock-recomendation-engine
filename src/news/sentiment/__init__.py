"""Sentiment analyzers. Implementations live behind :class:`SentimentAnalyzer`."""

from src.news.sentiment.base import SentimentAnalyzer, SentimentAnalyzerError
from src.news.sentiment.textblob import TextBlobSentimentAnalyzer

__all__ = [
    "SentimentAnalyzer",
    "SentimentAnalyzerError",
    "TextBlobSentimentAnalyzer",
]
