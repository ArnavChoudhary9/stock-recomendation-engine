"""Unit tests for OpenRouterProvider — JSON parsing and error translation."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import (
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from src.config import LLMProviderConfig
from src.contracts import StockReport
from src.llm.providers.base import (
    LLMAuthError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.llm.providers.openrouter import OpenRouterProvider
from tests.unit._llm_fixtures import VALID_LLM_JSON


class _FakeClient:
    """Stand-in for AsyncOpenAI with a programmable create() outcome."""

    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome
        self.last_kwargs: dict[str, Any] | None = None

        async def _create(**kwargs: Any) -> Any:
            self.last_kwargs = kwargs
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


def _completion(content: str) -> Any:
    """Shape-compatible with ChatCompletion for our usage."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _config() -> LLMProviderConfig:
    return LLMProviderConfig(api_key="test-key")


def _mock_response(status: int) -> httpx.Response:
    return httpx.Response(
        status,
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )


@pytest.mark.asyncio
async def test_parses_plain_json_response() -> None:
    client = _FakeClient(_completion(VALID_LLM_JSON))
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    report = await provider.generate(
        prompt="p", system="s", schema=StockReport, model="primary/model"
    )

    assert isinstance(report, StockReport)
    assert client.last_kwargs is not None
    assert client.last_kwargs["model"] == "primary/model"
    assert client.last_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_strips_markdown_fences_around_json() -> None:
    fenced = f"```json\n{VALID_LLM_JSON}\n```"
    client = _FakeClient(_completion(fenced))
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    report = await provider.generate(
        prompt="p", system="s", schema=StockReport, model="m"
    )
    assert isinstance(report, StockReport)


@pytest.mark.asyncio
async def test_invalid_json_raises_invalid_response() -> None:
    client = _FakeClient(_completion("not json at all"))
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")


@pytest.mark.asyncio
async def test_schema_validation_failure_raises_invalid_response() -> None:
    bad = json.dumps({"symbol": "X"})  # missing required fields
    client = _FakeClient(_completion(bad))
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")


@pytest.mark.asyncio
async def test_empty_content_raises_invalid_response() -> None:
    client = _FakeClient(_completion(""))
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")


@pytest.mark.asyncio
async def test_rate_limit_translated() -> None:
    err = RateLimitError("throttled", response=_mock_response(429), body=None)
    client = _FakeClient(err)
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMRateLimitError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")


@pytest.mark.asyncio
async def test_timeout_translated() -> None:
    err = APITimeoutError(
        httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )
    client = _FakeClient(err)
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMTimeoutError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")


@pytest.mark.asyncio
async def test_auth_error_translated() -> None:
    err = AuthenticationError("bad key", response=_mock_response(401), body=None)
    client = _FakeClient(err)
    provider = OpenRouterProvider(_config(), client=client)  # type: ignore[arg-type]

    with pytest.raises(LLMAuthError):
        await provider.generate(prompt="p", system="s", schema=StockReport, model="m")
