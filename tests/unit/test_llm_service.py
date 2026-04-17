"""Unit tests for the LLMService orchestration (fallback, retry, degraded)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from src.config import LLMConfig, LLMProviderConfig
from src.contracts import StockReport
from src.llm.providers.base import (
    LLMInvalidResponseError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.llm.service import LLMService
from tests.unit._llm_fixtures import VALID_LLM_JSON, make_analysis, make_news


class ScriptedProvider(LLMProvider):
    """Returns responses per-model per-attempt from a scripted plan.

    Plan: dict mapping model name → list of outcomes, consumed left-to-right.
    An outcome is either a ``StockReport`` instance (success) or an ``Exception``
    instance (raised on that call).
    """

    name = "scripted"

    def __init__(self, plan: dict[str, list[StockReport | Exception]]) -> None:
        self.plan = {m: list(outs) for m, outs in plan.items()}
        self.calls: list[tuple[str, str]] = []

    async def generate(
        self, *, prompt: str, system: str, schema: type, model: str
    ) -> StockReport:
        self.calls.append((model, prompt[:40]))
        if model not in self.plan or not self.plan[model]:
            raise LLMTimeoutError(f"no more scripted outcomes for {model}")
        outcome = self.plan[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _canned_report() -> StockReport:
    data = json.loads(VALID_LLM_JSON)
    return StockReport.model_validate(data)


def _config(*, fallbacks: list[str] | None = None, retries: int = 2) -> LLMConfig:
    return LLMConfig(
        llm=LLMProviderConfig(
            api_key="test",
            model="primary/model",
            fallback_models=fallbacks or [],
            max_retries=retries,
            backoff_base_seconds=0.0,  # no actual sleeping in tests
        )
    )


@pytest.mark.asyncio
async def test_primary_success_returns_report_with_authoritative_fields() -> None:
    provider = ScriptedProvider({"primary/model": [_canned_report()]})
    svc = LLMService(provider, _config())
    analysis = make_analysis(symbol="TCS")
    news = make_news(symbol="TCS")

    report = await svc.generate_report(analysis, news)

    assert report.symbol == "TCS"  # overwritten from analysis, not LLM's "IGNORED"
    assert report.model_used == "primary/model"
    assert report.degraded is False
    assert abs((report.timestamp - datetime.now(UTC)).total_seconds()) < 5
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_retries_transient_error_then_succeeds_on_same_model() -> None:
    provider = ScriptedProvider(
        {"primary/model": [LLMRateLimitError("throttled"), _canned_report()]}
    )
    svc = LLMService(provider, _config(retries=3))

    report = await svc.generate_report(make_analysis(), make_news())

    assert report.degraded is False
    assert len(provider.calls) == 2
    assert all(call[0] == "primary/model" for call in provider.calls)


@pytest.mark.asyncio
async def test_falls_back_to_secondary_when_primary_exhausts_retries() -> None:
    provider = ScriptedProvider(
        {
            "primary/model": [LLMTimeoutError("t"), LLMTimeoutError("t")],
            "fallback/a": [_canned_report()],
        }
    )
    svc = LLMService(provider, _config(fallbacks=["fallback/a"], retries=2))

    report = await svc.generate_report(make_analysis(), make_news())

    assert report.model_used == "fallback/a"
    assert report.degraded is False
    primary_calls = [c for c in provider.calls if c[0] == "primary/model"]
    fallback_calls = [c for c in provider.calls if c[0] == "fallback/a"]
    assert len(primary_calls) == 2  # retries exhausted
    assert len(fallback_calls) == 1


@pytest.mark.asyncio
async def test_degraded_report_when_all_models_fail() -> None:
    provider = ScriptedProvider(
        {
            "primary/model": [LLMTimeoutError("t")] * 2,
            "fallback/a": [LLMRateLimitError("r")] * 2,
            "fallback/b": [LLMInvalidResponseError("bad json")] * 2,
        }
    )
    svc = LLMService(
        provider,
        _config(fallbacks=["fallback/a", "fallback/b"], retries=2),
    )

    report = await svc.generate_report(make_analysis(symbol="INFY"), make_news(symbol="INFY"))

    assert report.degraded is True
    assert report.model_used is None
    assert report.symbol == "INFY"
    assert report.confidence == 0.0
    assert "LLM unavailable" in report.summary


@pytest.mark.asyncio
async def test_symbol_mismatch_between_analysis_and_news_raises() -> None:
    svc = LLMService(ScriptedProvider({}), _config())
    with pytest.raises(ValueError, match="symbol mismatch"):
        await svc.generate_report(make_analysis(symbol="TCS"), make_news(symbol="INFY"))


@pytest.mark.asyncio
async def test_invalid_response_triggers_retry_then_fallback() -> None:
    provider = ScriptedProvider(
        {
            "primary/model": [LLMInvalidResponseError("schema")] * 2,
            "fallback/a": [_canned_report()],
        }
    )
    svc = LLMService(provider, _config(fallbacks=["fallback/a"], retries=2))

    report = await svc.generate_report(make_analysis(), make_news())

    assert report.model_used == "fallback/a"
    assert report.degraded is False
