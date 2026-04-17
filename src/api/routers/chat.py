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
from src.llm.service import LLMService
from src.processing.service import DefaultProcessingService, ProcessingError

router = APIRouter(prefix="/chat", tags=["chat"])

log = logging.getLogger(__name__)

_BASE_SYSTEM_PROMPT = (
    "You are a concise financial analyst for a personal Indian-equities "
    "stock-intelligence platform (NSE/BSE). You help the user reason about "
    "the deterministic scoring output, market signals, and news. Answer in "
    "short paragraphs with clear, numbered steps when useful. Never invent "
    "prices, scores, or URLs — if a fact isn't in the provided context, say so."
)


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    llm: LLMService = Depends(get_llm_service),
    processing: DefaultProcessingService = Depends(get_processing_service),
) -> StreamingResponse:
    """Stream NDJSON deltas back to the client."""
    context_block = await _build_context_block(payload.context_symbols, processing)
    system_prompt = _BASE_SYSTEM_PROMPT
    if context_block:
        system_prompt = f"{_BASE_SYSTEM_PROMPT}\n\n{context_block}"

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


async def _build_context_block(
    symbols: list[str], processing: DefaultProcessingService
) -> str:
    """Render a compact 'current state' block for each requested symbol.

    Missing or failing symbols are listed inline so the model knows the user
    asked about them but no data is available.
    """
    if not symbols:
        return ""
    lines: list[str] = ["Context — latest deterministic analysis for the user's active symbols:"]
    for sym in symbols:
        try:
            analysis = await processing.analyze_stock(sym)
        except ProcessingError as e:
            log.debug("chat context missing for %s: %s", sym, e)
            lines.append(f"- {sym}: no analysis available ({e}).")
            continue
        lines.append(_format_analysis_line(analysis))
    return "\n".join(lines)


def _format_analysis_line(a: StockAnalysis) -> str:
    ma = a.moving_averages
    mom = a.features.momentum
    active_signals = [k for k, v in a.signals.items() if v]
    signals_str = ", ".join(active_signals) if active_signals else "none"
    return (
        f"- {a.symbol}: score={a.score:.2f}, reco={a.recommendation}, "
        f"last_close={a.features.last_close:.2f}, rsi14={mom.rsi_14:.0f}, "
        f"5d={mom.return_5d * 100:+.1f}%, 20d={mom.return_20d * 100:+.1f}%, "
        f"ma_alignment={ma.alignment}, signals=[{signals_str}]."
    )


def _frame(obj: dict[str, object]) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
