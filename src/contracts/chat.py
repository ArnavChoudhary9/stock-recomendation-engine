"""Chat contracts — request payload for ``POST /api/v1/chat/stream``.

The chat endpoint streams plain-text deltas (NDJSON) rather than returning a
single structured envelope, so there is no response contract here — only the
incoming request shape is validated.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ChatRole = Literal["system", "user", "assistant"]


class ChatTurn(BaseModel):
    """A single turn in a chat conversation."""

    model_config = ConfigDict(frozen=True)

    role: ChatRole
    content: str = Field(..., min_length=1)


class ChatStreamRequest(BaseModel):
    """POST body for ``/chat/stream``."""

    model_config = ConfigDict(frozen=True)

    messages: list[ChatTurn] = Field(..., min_length=1)
    context_symbols: list[str] = Field(default_factory=list)

    @field_validator("context_symbols")
    @classmethod
    def _upper_symbols(cls, v: list[str]) -> list[str]:
        return [s.strip().upper() for s in v if s and s.strip()]
