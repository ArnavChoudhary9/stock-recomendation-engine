"""Unit tests for LLM prompt rendering (Jinja2 template)."""

from __future__ import annotations

from src.config import LLMConfig
from src.contracts import StockReport
from src.llm.providers.base import LLMProvider
from src.llm.service import LLMService
from tests.unit._llm_fixtures import make_analysis, make_news


class _NullProvider(LLMProvider):
    name = "null"

    async def generate(
        self, *, prompt: str, system: str, schema: type, model: str
    ) -> StockReport:  # pragma: no cover - never called in prompt tests
        raise NotImplementedError


def _service() -> LLMService:
    return LLMService(provider=_NullProvider(), config=LLMConfig())


def test_prompt_includes_symbol_and_score() -> None:
    svc = _service()
    prompt = svc._render_prompt(make_analysis(), make_news())
    assert "RELIANCE" in prompt
    assert "0.720" in prompt


def test_prompt_includes_moving_average_details() -> None:
    svc = _service()
    prompt = svc._render_prompt(make_analysis(), make_news())
    assert "SMA20 / SMA50 / SMA200: 2950.00 / 2880.00 / 2700.00" in prompt
    assert "Alignment: bullish" in prompt
    assert "golden_cross" in prompt


def test_prompt_includes_news_aggregate_and_headlines() -> None:
    svc = _service()
    news = make_news(count=2)
    prompt = svc._render_prompt(make_analysis(), news)
    assert "3 article(s)" not in prompt
    assert "2 article(s)" in prompt
    assert "+0.220" in prompt
    assert "strong quarterly results #0" in prompt


def test_prompt_handles_no_news() -> None:
    svc = _service()
    prompt = svc._render_prompt(make_analysis(), make_news(count=0))
    assert "No recent news available." in prompt


def test_prompt_includes_all_signals() -> None:
    svc = _service()
    prompt = svc._render_prompt(make_analysis(), make_news())
    for signal in ("golden_cross", "ma_bullish_stack", "momentum_strong", "overbought"):
        assert signal in prompt


def test_system_prompt_contains_schema_and_rules() -> None:
    svc = _service()
    sp = svc._system_prompt
    assert "StockReport" in sp
    assert "confidence" in sp
    assert "Never invent numbers" in sp
