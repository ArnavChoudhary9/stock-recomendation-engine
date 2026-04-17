"""Run the full stock pipeline: data → analysis → news → LLM report.

Unlike ``run_pipeline.py`` (scoring only), this script exercises every layer
end-to-end for a handful of symbols and prints a human-readable report that
combines:

* Quantitative analysis (score, sub-scores, signals, moving averages)
* News bundle (recent headlines, aggregate sentiment)
* LLM narrative (summary, insights, risks, news impact)

Prerequisites: the database should already have OHLCV + fundamentals for the
requested symbols (run ``scripts/backfill.py`` first). ``OPENROUTER_API_KEY``
is required for the LLM layer; without it, a degraded placeholder report is
returned instead of crashing. ``NEWSAPI_KEY`` is optional — falls back to
Google News RSS when unset.

Examples::

    python scripts/full_report.py --symbols RELIANCE,TCS
    python scripts/full_report.py --preset nifty50 --top 5
    python scripts/full_report.py --symbols INFY --format json > infy.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    CONFIG_DIR,
    ConfigError,
    LLMConfig,
    load_data_config,
    load_llm_config,
    load_news_config,
    load_processing_config,
)
from src.contracts import NewsBundle, StockAnalysis, StockReport
from src.data.providers.yahoo import YahooFinanceProvider
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.llm.providers.openrouter import OpenRouterProvider
from src.llm.service import LLMService
from src.news.service import NewsService, build_news_service
from src.processing.service import DefaultProcessingService, ProcessingError

log = logging.getLogger("full_report")

PRESETS_DIR = CONFIG_DIR / "symbols"


# --- CLI + symbol resolution ----------------------------------------------


def _read_symbols_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"symbols file not found: {path}")
    syms: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            syms.append(line.upper())
    return syms


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        return _read_symbols_file(Path(args.symbols_file))
    if args.preset:
        return _read_symbols_file(PRESETS_DIR / f"{args.preset}.txt")
    raise SystemExit("one of --symbols, --symbols-file, or --preset is required")


# --- Pipeline bundle ------------------------------------------------------


class _ReportBundle:
    """Everything we've gathered for a single stock."""

    def __init__(
        self,
        symbol: str,
        analysis: StockAnalysis,
        news: NewsBundle,
        report: StockReport,
        company_name: str | None,
    ) -> None:
        self.symbol = symbol
        self.analysis = analysis
        self.news = news
        self.report = report
        self.company_name = company_name

    def to_json(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "analysis": self.analysis.model_dump(mode="json"),
            "news": self.news.model_dump(mode="json"),
            "report": self.report.model_dump(mode="json"),
        }


# --- Formatted output -----------------------------------------------------


def _print_bundle(b: _ReportBundle) -> None:
    a = b.analysis
    r = b.report
    n = b.news

    print("=" * 80)
    header = f"{a.symbol}"
    if b.company_name:
        header += f"  ({b.company_name})"
    print(header)
    print("=" * 80)

    active = [k for k, v in a.signals.items() if v is True]
    print(
        f"Score:   {a.score:0.3f}    Last close: {a.features.last_close:,.2f}    "
        f"Quant call: {a.recommendation}"
    )
    if a.recommendation_rationale:
        print(f"  quant rationale: {a.recommendation_rationale}")
    print(f"Signals: {', '.join(active) or '-'}")
    print(
        "Subscores: "
        f"MA={a.sub_scores.moving_average:.2f}  "
        f"Mom={a.sub_scores.momentum:.2f}  "
        f"Vol={a.sub_scores.volume:.2f}  "
        f"Volty={a.sub_scores.volatility:.2f}  "
        f"Fund={a.sub_scores.fundamental:.2f}  "
        f"SR={a.sub_scores.support_resistance:.2f}"
    )

    ma = a.moving_averages
    cross = f"{ma.crossover} ({ma.crossover_days_ago}d ago)" if ma.crossover else "none"
    print(
        f"MAs:     SMA20={ma.sma_20:,.2f}  SMA50={ma.sma_50:,.2f}  SMA200={ma.sma_200:,.2f}  "
        f"alignment={ma.alignment}  crossover={cross}"
    )

    print()
    print(f"News ({n.article_count} in last {n.time_window_hours}h, "
          f"aggregate sentiment {n.aggregate_sentiment:+.3f}):")
    if not n.articles:
        print("  (none)")
    for art in n.articles[:5]:
        print(
            f"  [{art.sentiment.label:>8} {art.sentiment.score:+.2f}] "
            f"{art.title}  — {art.source}"
        )

    print()
    model_tag = r.model_used or "unavailable"
    degraded_tag = "  (DEGRADED)" if r.degraded else ""
    print(f"LLM report [{model_tag}]{degraded_tag}  confidence={r.confidence:.2f}")
    agree = "agrees" if r.recommendation == a.recommendation else "DIFFERS from quant"
    print(f"LLM call: {r.recommendation} ({agree})")
    if r.recommendation_rationale:
        print(f"  LLM rationale: {r.recommendation_rationale}")
    print(f"Summary: {r.summary}")
    if r.insights:
        print("Insights:")
        for ins in r.insights:
            print(f"  + {ins}")
    if r.risks:
        print("Risks:")
        for risk in r.risks:
            print(f"  - {risk}")
    print(f"News impact: {r.news_impact}")
    if r.reasoning_chain:
        print("Reasoning:")
        for step in r.reasoning_chain:
            print(f"  > {step}")
    if r.sources:
        print("Sources:")
        for src in r.sources:
            print(f"  • [{src.sentiment_label} {src.sentiment_score:+.2f}] "
                  f"{src.title}  — {src.source}  — {src.url}")
    print()


# --- Service wiring -------------------------------------------------------


def _build_llm_service() -> LLMService | None:
    """Return an LLMService, or None if ``OPENROUTER_API_KEY`` is unset/config missing.

    We swallow :class:`ConfigError` because ``config/llm.yaml`` interpolates
    ``${OPENROUTER_API_KEY}`` at load time — unset env → ConfigError.
    """
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        log.warning("OPENROUTER_API_KEY not set — LLM reports will be degraded")
        return _degraded_llm_service()
    try:
        llm_cfg = load_llm_config()
    except ConfigError as e:
        log.warning("LLM config unavailable (%s) — degraded reports only", e)
        return _degraded_llm_service()
    return LLMService(OpenRouterProvider(llm_cfg.llm), llm_cfg)


def _degraded_llm_service() -> LLMService:
    """LLMService wired to an unreachable provider so every call degrades cleanly."""
    cfg = LLMConfig()  # defaults — ``api_key`` empty, causes auth error on use
    provider = OpenRouterProvider(cfg.llm)
    return LLMService(provider, cfg)


# --- Main -----------------------------------------------------------------


async def _gather_for_symbol(
    symbol: str,
    *,
    data_service: DataService,
    processor: DefaultProcessingService,
    news_service: NewsService,
    llm_service: LLMService,
) -> _ReportBundle | None:
    try:
        analysis = await processor.analyze_stock(symbol)
    except ProcessingError as e:
        log.warning("skipping %s: %s", symbol, e)
        return None

    stock_info = await data_service.ensure_stock(symbol)
    company_name = stock_info.name if stock_info else None

    news = await news_service.get_news(symbol, company_name=company_name)
    report = await llm_service.generate_report(analysis, news)
    return _ReportBundle(symbol, analysis, news, report, company_name)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Full pipeline: analysis + news + LLM report")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="Comma-separated symbols")
    src.add_argument("--symbols-file", help="Path to a newline-delimited symbols file")
    src.add_argument(
        "--preset",
        choices=[p.stem for p in PRESETS_DIR.glob("*.txt")] or ["nifty50"],
        help="Named symbol list from config/symbols/",
    )
    parser.add_argument("--top", type=int, default=None, help="Limit to top N by score")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--lookback-days", type=int, default=400,
        help="OHLCV window to pull from the repo (must exceed SMA(200))",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    symbols = _resolve_symbols(args)

    data_cfg = load_data_config()
    scoring_cfg = load_processing_config()
    news_cfg = load_news_config()

    repo = SQLiteStockRepository(data_cfg.storage.path, wal_mode=data_cfg.storage.wal_mode)
    await repo.init()
    bundles: list[_ReportBundle] = []
    try:
        provider = YahooFinanceProvider(
            default_exchange=data_cfg.data.default_exchange,
            min_interval_ms=data_cfg.data.rate_limit_delay_ms,
        )
        data_service = DataService(provider, repo, data_cfg)
        processor = DefaultProcessingService(
            data_service, scoring_cfg, lookback_days=args.lookback_days
        )
        news_service = build_news_service(news_cfg)
        llm_service = _build_llm_service()
        assert llm_service is not None  # _build_llm_service always returns a service

        log.info("processing %d symbol(s)…", len(symbols))
        for sym in symbols:
            bundle = await _gather_for_symbol(
                sym,
                data_service=data_service,
                processor=processor,
                news_service=news_service,
                llm_service=llm_service,
            )
            if bundle is not None:
                bundles.append(bundle)
    finally:
        await repo.close()

    bundles.sort(key=lambda b: b.analysis.score, reverse=True)
    if args.top is not None:
        bundles = bundles[: args.top]

    if args.format == "json":
        payload = [b.to_json() for b in bundles]
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        if not bundles:
            print("(no symbols produced a full report)")
        for b in bundles:
            _print_bundle(b)

    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(asyncio.run(main()))
