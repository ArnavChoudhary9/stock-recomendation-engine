"""LLMProvider abstract interface.

Pluggable LLM backend. All implementations must translate raw model output
into a validated Pydantic instance matching the requested ``schema``.
Providers never touch contracts from sibling modules — only what's passed in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    """One turn in a chat conversation — provider-agnostic representation."""

    role: ChatRole
    content: str


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

    def stream_chat(
        self,
        *,
        messages: list[ChatMessage],
        model: str,
    ) -> AsyncIterator[str]:
        """Stream plain-text completion deltas for a chat conversation.

        Unlike :meth:`generate`, this is free-form text — no JSON schema,
        no validation. Default implementation raises — providers opt in by
        overriding. Callers should treat ``NotImplementedError`` as a
        "chat not supported by this backend" signal.

        Raises
        ------
        LLMTimeoutError, LLMRateLimitError, LLMAuthError, LLMError
            Terminal failures. Chat streaming is single-shot; retries + model
            fallback are the caller's responsibility.
        NotImplementedError
            The provider does not support chat streaming.
        """
        del messages, model
        raise NotImplementedError(
            f"{type(self).__name__} does not support chat streaming"
        )
