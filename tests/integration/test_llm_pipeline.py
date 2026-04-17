"""Integration test: full input → LLM provider → validated StockReport.

Uses a fake provider that returns canned JSON so the test runs offline and
deterministically, but exercises the real prompt rendering, system-prompt
assembly, schema validation, and authoritative-field finalization.
"""

from __future__ import annotations

import json

import pytest

from src.config import LLMConfig, LLMProviderConfig
from src.contracts import StockReport
from src.llm.providers.base import LLMProvider
from src.llm.service import LLMService
from tests.unit._llm_fixtures import VALID_LLM_JSON, make_analysis, make_news


class CannedJSONProvider(LLMProvider):
    """Round-trips a canned JSON body through StockReport validation.

    Mimics a real provider: it accepts a schema and returns a parsed instance.
    """

    name = "canned"

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.seen_prompts: list[str] = []
        self.seen_systems: list[str] = []
        self.seen_models: list[str] = []

    async def generate(
        self, *, prompt: str, system: str, schema: type, model: str
    ) -> StockReport:
        self.seen_prompts.append(prompt)
        self.seen_systems.append(system)
        self.seen_models.append(model)
        return schema.model_validate(json.loads(self.payload))


@pytest.mark.asyncio
async def test_end_to_end_report_generation() -> None:
    provider = CannedJSONProvider(VALID_LLM_JSON)
    config = LLMConfig(
        llm=LLMProviderConfig(
            api_key="test",
            model="anthropic/claude-sonnet-4",
            backoff_base_seconds=0.0,
        )
    )
    svc = LLMService(provider, config)

    analysis = make_analysis(symbol="HDFCBANK", score=0.81)
    news = make_news(symbol="HDFCBANK", count=4)

    report = await svc.generate_report(analysis, news)

    # Authoritative fields filled by the service, not the LLM
    assert report.symbol == "HDFCBANK"
    assert report.model_used == "anthropic/claude-sonnet-4"
    assert report.degraded is False

    # Narrative content preserved from the LLM
    assert report.summary.startswith("RELIANCE")
    assert len(report.insights) == 3
    assert len(report.risks) == 2
    assert 0.0 <= report.confidence <= 1.0

    # LLM's own recommendation survives the round-trip
    assert report.recommendation == "BUY"
    assert "BUY" in report.recommendation_rationale.upper() or report.recommendation_rationale

    # Sources auto-filled from NewsBundle (not the LLM) to prevent hallucinated URLs
    assert len(report.sources) == 4
    assert str(report.sources[0].url).startswith("https://example.com/hdfcbank/")

    # Provider was handed a prompt populated from the real Jinja template
    rendered = provider.seen_prompts[0]
    assert "HDFCBANK" in rendered
    assert "0.810" in rendered
    assert "4 article(s)" in rendered

    # System prompt embeds the schema so any OpenRouter-routed model can comply
    assert "StockReport" in provider.seen_systems[0]
