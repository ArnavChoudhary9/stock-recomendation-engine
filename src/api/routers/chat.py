"""`/api/v1/chat/stream` — streaming conversational endpoint.

Wire format: newline-delimited JSON (one object per line). Each frame is one of:
    {"delta": "<partial text>"}
    {"done": true}
    {"error": "<message>"}

Chat context is injected into a synthetic system prompt built from the latest
``StockAnalysis`` for each ``context_symbols`` entry. News is intentionally
*not* fetched inline (latency) — the UI surfaces news on the stock detail page.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_llm_service, get_processing_service
from src.contracts import ChatStreamRequest, StockAnalysis
from src.llm.providers.base import (
    ChatMessage,
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.llm.render import render
from src.llm.service import LLMService
from src.processing.service import DefaultProcessingService, ProcessingError

router = APIRouter(prefix="/chat", tags=["chat"])

log = logging.getLogger(__name__)

CHAT_SYSTEM_TEMPLATE = "chat_system.j2"
CHAT_CONTEXT_TEMPLATE = "chat_context.j2"


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    llm: LLMService = Depends(get_llm_service),
    processing: DefaultProcessingService = Depends(get_processing_service),
) -> StreamingResponse:
    """Stream NDJSON deltas back to the client."""
    entries = await _collect_context_entries(payload.context_symbols, processing)
    system_prompt = render(CHAT_SYSTEM_TEMPLATE).strip()
    if entries:
        system_prompt = (
            f"{system_prompt}\n\n"
            f"{render(CHAT_CONTEXT_TEMPLATE, entries=entries).strip()}"
        )

    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
    messages.extend(ChatMessage(role=m.role, content=m.content) for m in payload.messages)

    async def body() -> AsyncIterator[bytes]:
        try:
            async for delta in llm.stream_chat(messages):
                yield _frame({"delta": delta})
            yield _frame({"done": True})
        except LLMAuthError as e:
            log.warning("chat stream auth error: %s", e)
            yield _frame({"error": "LLM authentication failed — check OPENROUTER_API_KEY."})
        except LLMRateLimitError as e:
            log.info("chat stream rate-limited: %s", e)
            yield _frame({"error": "LLM rate-limited. Try again in a few seconds."})
        except LLMTimeoutError as e:
            log.info("chat stream timeout: %s", e)
            yield _frame({"error": "LLM request timed out."})
        except LLMError as e:
            log.exception("chat stream LLM error")
            yield _frame({"error": f"LLM error: {e}"})
        except Exception as e:  # pragma: no cover — defensive
            log.exception("chat stream unexpected error")
            yield _frame({"error": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        body(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _collect_context_entries(
    symbols: list[str], processing: DefaultProcessingService
) -> list[dict[str, object]]:
    """Collect one context entry per requested symbol, keeping order.

    Successful lookups contribute ``{"symbol", "analysis", "signals_str"}``;
    failures contribute ``{"symbol", "error"}``. The chat_context.j2 template
    branches on which key is present so both cases render inline.
    """
    entries: list[dict[str, object]] = []
    for sym in symbols:
        try:
            analysis = await processing.analyze_stock(sym)
        except ProcessingError as e:
            log.debug("chat context missing for %s: %s", sym, e)
            # Keep both keys present so StrictUndefined in Jinja doesn't trip.
            entries.append(
                {"symbol": sym, "analysis": None, "error": str(e), "signals_str": ""}
            )
            continue
        entries.append(
            {
                "symbol": sym,
                "analysis": analysis,
                "error": None,
                "signals_str": _active_signals_str(analysis),
            }
        )
    return entries


def _active_signals_str(a: StockAnalysis) -> str:
    active = [k for k, v in a.signals.items() if v]
    return ", ".join(active) if active else "none"


def _frame(obj: dict[str, object]) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
