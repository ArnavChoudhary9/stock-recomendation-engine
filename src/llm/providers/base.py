"""LLMProvider abstract interface.

Pluggable LLM backend. All implementations must translate raw model output
into a validated Pydantic instance matching the requested ``schema``.
Providers never touch contracts from sibling modules — only what's passed in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base class for LLM provider failures."""


class LLMTimeoutError(LLMError):
    """Upstream request exceeded the configured timeout."""


class LLMRateLimitError(LLMError):
    """Upstream throttled the request (HTTP 429)."""


class LLMInvalidResponseError(LLMError):
    """Response could not be parsed or failed schema validation."""


class LLMAuthError(LLMError):
    """Authentication rejected (bad or missing API key)."""


class LLMAllModelsFailedError(LLMError):
    """Every model in the fallback chain exhausted its retries."""


class LLMProvider(ABC):
    """Contract for an LLM backend that returns structured output."""

    name: str

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        system: str,
        schema: type[T],
        model: str,
    ) -> T:
        """Run inference and return a validated instance of ``schema``.

        Raises
        ------
        LLMTimeoutError, LLMRateLimitError, LLMInvalidResponseError, LLMAuthError
            Transient or terminal failures. The service layer decides how to
            handle fallback across models.
        """
