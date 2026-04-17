"""OpenRouter LLM provider.

OpenRouter exposes an OpenAI-compatible API routing to many underlying models
(Claude, GPT, Llama, Gemini, etc.). A single API key plus a configurable model
string is all we need — model switching is pure config, no code changes.

The provider requests JSON output via both the system prompt (enforced by the
service layer) and ``response_format={"type": "json_object"}`` when supported.
Parsing is tolerant: markdown fences around the JSON body are stripped before
validation so models that wrap output in ```json``` blocks still succeed.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from src.config import LLMProviderConfig
from src.llm.providers.base import (
    LLMAuthError,
    LLMError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
)

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


class OpenRouterProvider(LLMProvider):
    """OpenRouter-backed LLM provider using the OpenAI-compatible client."""

    name = "openrouter"

    def __init__(
        self,
        config: LLMProviderConfig,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.config = config
        self._client = client or AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    async def generate(
        self,
        *,
        prompt: str,
        system: str,
        schema: type[T],
        model: str,
    ) -> T:
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"},
            )
        except AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except (APITimeoutError, APIConnectionError) as e:
            raise LLMTimeoutError(str(e)) from e
        except APIStatusError as e:
            if e.status_code == 429:
                raise LLMRateLimitError(str(e)) from e
            if e.status_code in (401, 403):
                raise LLMAuthError(str(e)) from e
            raise LLMError(f"OpenRouter returned HTTP {e.status_code}: {e}") from e

        if not response.choices:
            raise LLMInvalidResponseError("No choices returned by OpenRouter")
        content = response.choices[0].message.content
        if not content:
            raise LLMInvalidResponseError("Empty content in OpenRouter response")

        payload = _strip_markdown_fence(content)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            log.debug("Invalid JSON from model %s: %s", model, content[:500])
            raise LLMInvalidResponseError(f"Model {model} returned non-JSON: {e}") from e

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            raise LLMInvalidResponseError(
                f"Model {model} output failed schema validation: {e.errors()}"
            ) from e


def _strip_markdown_fence(text: str) -> str:
    match = _JSON_FENCE.match(text)
    return match.group(1) if match else text.strip()
