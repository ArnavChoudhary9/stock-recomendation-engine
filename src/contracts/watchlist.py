"""Watchlist contracts.

A watchlist is a user-curated list of symbols to keep an eye on, separate
from what's tracked in the stocks table. Adding a symbol here doesn't
automatically backfill OHLCV — the caller still needs to trigger that.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WatchlistItem(BaseModel):
    """A single entry on the user's watchlist."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., min_length=1, max_length=32)
    added_at: datetime
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class AddToWatchlistRequest(BaseModel):
    """Body schema for POST /watchlist."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
