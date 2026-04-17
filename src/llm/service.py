"""LLMService — orchestrates prompt assembly, model fallback, and output normalization.

The LLM **augments** the deterministic analysis: it never alters the score or
signals. This service renders a Jinja2 prompt from ``StockAnalysis`` + ``NewsBundle``,
asks a provider to produce a structured :class:`StockReport`, and runs a
fallback chain over configured models with exponential-backoff retries per model.

If every model in the chain exhausts its retries, a *degraded* placeholder
report is returned so downstream callers never crash on LLM unavailability.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from src.config import LLMConfig
from src.contracts import Article, NewsBundle, NewsReference, StockAnalysis, StockReport
from src.llm.providers.base import (
    LLMAllModelsFailedError,
    LLMAuthError,
    LLMError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
)

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
STOCK_REPORT_TEMPLATE = "stock_report.j2"

# Transient errors → retry the same model. Auth errors → don't retry; skip model entirely.
_RETRYABLE = (LLMRateLimitError, LLMTimeoutError, LLMInvalidResponseError)


class LLMService:
    """Generate human-readable stock reports via an LLM provider."""

    def __init__(self, provider: LLMProvider, config: LLMConfig) -> None:
        self.provider = provider
        self.config = config
        self._env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape(disabled_extensions=("j2",)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=False,
        )
        self._system_prompt = _build_system_prompt()

    async def generate_report(
        self, analysis: StockAnalysis, news: NewsBundle
    ) -> StockReport:
        """Render prompt, run the model fallback chain, return a validated report.

        Always returns a :class:`StockReport`. If every model fails, returns a
        degraded report with ``degraded=True`` instead of raising — the system
        must keep working when the LLM is unavailable.
        """
        if analysis.symbol != news.symbol:
            raise ValueError(
                f"symbol mismatch: analysis={analysis.symbol} news={news.symbol}"
            )

        user_prompt = self._render_prompt(analysis, news)
        models = [self.config.llm.model, *self.config.llm.fallback_models]

        sources = _sources_from_news(news)

        last_error: LLMError | None = None
        for model in models:
            try:
                report = await self._call_with_retries(user_prompt, model)
            except LLMAuthError as e:
                log.warning("auth error for model %s — skipping: %s", model, e)
                last_error = e
                continue
            except LLMError as e:
                log.warning("model %s exhausted retries: %s", model, e)
                last_error = e
                continue
            return _finalize_report(report, analysis.symbol, model, sources)

        log.error(
            "all LLM models failed for %s; returning degraded report (last error: %s)",
            analysis.symbol,
            last_error,
        )
        return _degraded_report(analysis.symbol, last_error, sources)

    async def _call_with_retries(self, prompt: str, model: str) -> StockReport:
        """Try ``model`` up to ``max_retries`` times with exponential backoff."""
        attempts = max(self.config.llm.max_retries, 1)
        last: LLMError | None = None
        for attempt in range(attempts):
            try:
                return await self.provider.generate(
                    prompt=prompt,
                    system=self._system_prompt,
                    schema=StockReport,
                    model=model,
                )
            except _RETRYABLE as e:
                last = e
                if attempt == attempts - 1:
                    break
                delay = self.config.llm.backoff_base_seconds * (2**attempt)
                log.info(
                    "retryable failure on %s (attempt %d/%d): %s — sleeping %.2fs",
                    model,
                    attempt + 1,
                    attempts,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
        assert last is not None
        raise LLMAllModelsFailedError(str(last)) from last

    def _render_prompt(self, analysis: StockAnalysis, news: NewsBundle) -> str:
        template = self._env.get_template(STOCK_REPORT_TEMPLATE)
        return template.render(analysis=analysis, news=news)


def _build_system_prompt() -> str:
    """System prompt: role + JSON schema for :class:`StockReport` output."""
    schema = StockReport.model_json_schema()
    return (
        "You are a financial analyst writing for a personal stock-intelligence "
        "platform covering Indian equities (NSE/BSE). Your job is to explain the "
        "quantitative analysis that is provided — never to modify the score or "
        "add/remove stocks from the ranked universe.\n\n"
        "Respond with a single JSON object matching this schema exactly. Output "
        "JSON only, no markdown, no prose before or after:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Field rules:\n"
        "- summary: 2-3 sentences grounded in the provided facts.\n"
        "- insights: up to 5 concise bullish factors, one sentence each.\n"
        "- risks: up to 5 concise risk factors, one sentence each.\n"
        "- news_impact: 1-2 sentences describing how the recent news affects the outlook.\n"
        "- confidence: float in [0, 1] reflecting how much the data supports a clear view.\n"
        "- reasoning_chain: 3-5 short steps linking data points to conclusions.\n"
        "- recommendation: your own BUY/HOLD/SELL call weighing news, momentum,\n"
        "  and sentiment. You may agree or disagree with the deterministic\n"
        "  recommendation shown in the user message.\n"
        "- recommendation_rationale: 1-2 sentences. If you disagree with the\n"
        "  deterministic call, explicitly state why.\n"
        "- sources: return an empty array []. The service fills it from the\n"
        "  provided article list — do not invent URLs.\n"
        "- Leave `model_used` as null and `degraded` as false — service fills them.\n"
        "- Never invent numbers or URLs. Use only facts present in the user message."
    )


def _sources_from_news(news: NewsBundle) -> list[NewsReference]:
    """Project the news bundle's articles into compact citation references."""
    return [_article_to_reference(a) for a in news.articles]


def _article_to_reference(article: Article) -> NewsReference:
    return NewsReference(
        title=article.title,
        url=article.url,
        source=article.source,
        published_at=article.published_at,
        sentiment_score=article.sentiment.score,
        sentiment_label=article.sentiment.label,
    )


def _finalize_report(
    report: StockReport,
    symbol: str,
    model: str,
    sources: list[NewsReference],
) -> StockReport:
    """Overwrite LLM-chosen metadata with authoritative values from the service.

    ``sources`` is populated server-side (not by the LLM) to prevent URL
    hallucination — models are instructed to leave the array empty.
    """
    return report.model_copy(
        update={
            "symbol": symbol,
            "timestamp": datetime.now(UTC),
            "model_used": model,
            "degraded": False,
            "sources": sources,
        }
    )


def _degraded_report(
    symbol: str,
    last_error: LLMError | None,
    sources: list[NewsReference],
) -> StockReport:
    """Fallback report returned when every model in the chain fails."""
    reason = str(last_error) if last_error else "unknown error"
    return StockReport(
        symbol=symbol,
        timestamp=datetime.now(UTC),
        summary="LLM unavailable — no narrative insight generated for this run.",
        insights=[],
        risks=[],
        news_impact="LLM unavailable — see quantitative signals and news feed directly.",
        confidence=0.0,
        reasoning_chain=[f"All configured models failed: {reason}"],
        recommendation="HOLD",
        recommendation_rationale="LLM unavailable — defaulting to HOLD.",
        sources=sources,
        model_used=None,
        degraded=True,
    )
