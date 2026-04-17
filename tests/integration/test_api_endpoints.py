"""Integration tests for the FastAPI layer.

Each test spins up an ASGI client against a fresh app instance with a custom
:class:`ServiceContainer` whose repo points at a throwaway SQLite file and
whose news/LLM services are stubs. We bypass the production container factory
by pre-setting ``app.state.container`` before issuing requests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import API_PREFIX, create_app
from src.api.dependencies import ServiceContainer
from src.api.routers.reports import clear_cache as clear_report_cache
from src.config import (
    APIConfig,
    APIServerConfig,
    DataConfig,
    DataProviderConfig,
    NewsConfig,
    StorageConfig,
)
from src.contracts import (
    NewsBundle,
    RawArticle,
    ScoringConfig,
    StockReport,
)
from src.data.repositories.sqlite import SQLiteStockRepository
from src.data.service import DataService
from src.news.providers.base import NewsProvider
from src.news.sentiment.textblob import TextBlobSentimentAnalyzer
from src.news.service import NewsService
from src.processing.service import DefaultProcessingService
from tests.conftest import FakeProvider


class StubNewsProvider(NewsProvider):
    name = "stub"

    def __init__(self, articles: list[RawArticle] | None = None) -> None:
        self.articles = articles or []

    async def fetch_news(
        self, query: str, from_date: datetime, to_date: datetime, *, limit: int
    ) -> list[RawArticle]:
        del query
        return [a for a in self.articles if from_date <= a.published_at <= to_date][:limit]


class StubLLMService:
    """Minimal LLMService stand-in — returns a canned StockReport."""

    def __init__(self) -> None:
        self.calls = 0
        self.chat_calls: list[list] = []

    async def generate_report(self, analysis, news) -> StockReport:  # type: ignore[no-untyped-def]
        del news
        self.calls += 1
        return StockReport(
            symbol=analysis.symbol,
            timestamp=datetime.now(UTC),
            summary=f"Stub report for {analysis.symbol}",
            insights=["Mock insight"],
            risks=["Mock risk"],
            news_impact="Mock news impact",
            confidence=0.5,
            reasoning_chain=["Step 1", "Step 2"],
            model_used="stub/model",
            degraded=False,
        )

    async def stream_chat(self, messages):  # type: ignore[no-untyped-def]
        self.chat_calls.append(list(messages))
        for chunk in ("hello ", "world"):
            yield chunk


async def _make_container(tmp_path: Path, *, include_llm: bool = True) -> ServiceContainer:
    today = datetime.now(UTC).date()
    db_path = tmp_path / "api.db"
    repo = SQLiteStockRepository(db_path, wal_mode=False)
    await repo.init()

    provider = FakeProvider()
    provider.seed_ohlcv("TCS", today - timedelta(days=400), days=400)
    provider.seed_fundamentals("TCS")
    info = provider.seed_stock("TCS", name="Tata Consultancy", sector="IT")
    await repo.upsert_stock(info)

    data_cfg = DataConfig(
        data=DataProviderConfig(provider="fake", backfill_days=400, rate_limit_delay_ms=0),
        storage=StorageConfig(path=db_path, wal_mode=False),
    )
    scoring_cfg = ScoringConfig()
    news_cfg = NewsConfig()
    api_cfg = APIConfig(api=APIServerConfig())

    data_service = DataService(provider, repo, data_cfg)
    # Seed initial data so analysis has enough bars.
    await data_service.refresh_symbol("TCS")

    processing_service = DefaultProcessingService(data_service, scoring_cfg, lookback_days=400)
    news_service = NewsService(StubNewsProvider(), TextBlobSentimentAnalyzer(), news_cfg)

    return ServiceContainer(
        repo=repo,
        data_service=data_service,
        processing_service=processing_service,
        news_service=news_service,
        llm_service=StubLLMService() if include_llm else None,  # type: ignore[arg-type]
        data_config=data_cfg,
        scoring_config=scoring_cfg,
        news_config=news_cfg,
        llm_config=None,
        api_config=api_cfg,
        started_at=datetime.now(UTC),
    )


@pytest.fixture
async def client(tmp_path: Path):  # type: ignore[no-untyped-def]
    clear_report_cache()
    container = await _make_container(tmp_path)
    app = create_app(APIConfig(api=APIServerConfig()))
    app.state.container = container  # bypass lifespan
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        try:
            yield c
        finally:
            await container.repo.close()


@pytest.fixture
async def client_no_llm(tmp_path: Path):  # type: ignore[no-untyped-def]
    clear_report_cache()
    container = await _make_container(tmp_path, include_llm=False)
    app = create_app(APIConfig(api=APIServerConfig()))
    app.state.container = container
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        try:
            yield c
        finally:
            await container.repo.close()


# ---------------------------- System endpoints ----------------------------


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["components"]["db"] == "ok"
    assert "timestamp" in body["meta"]
    assert r.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_config_endpoint_returns_non_secret_snapshot(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/config")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["data"]["data"]["provider"] == "fake"
    # LLM was set in tests but llm_config is None, so the snapshot should reflect that.
    assert body["data"]["llm"] is None


@pytest.mark.asyncio
async def test_pipeline_run_returns_accepted(client: AsyncClient) -> None:
    r = await client.post(f"{API_PREFIX}/pipeline/run")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["scheduled"] is True
    assert body["data"]["symbols_count"] >= 1


# ---------------------------- Stocks endpoints ----------------------------


@pytest.mark.asyncio
async def test_list_stocks(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] >= 1
    symbols = [s["symbol"] for s in body["data"]]
    assert "TCS" in symbols


@pytest.mark.asyncio
async def test_list_stocks_filter_by_sector(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks", params={"sector": "IT"})
    assert r.status_code == 200
    for s in r.json()["data"]:
        assert s["sector"] == "IT"


@pytest.mark.asyncio
async def test_get_stock_detail(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/tcs")  # case-insensitive symbol
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["info"]["symbol"] == "TCS"
    assert body["data"]["fundamentals"] is not None
    assert body["data"]["latest_close"] is not None


@pytest.mark.asyncio
async def test_get_stock_detail_404(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/UNKNOWN")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_ohlcv_default_window(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/TCS/ohlcv", params={"days": 30})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1


@pytest.mark.asyncio
async def test_get_ohlcv_rejects_inverted_range(client: AsyncClient) -> None:
    r = await client.get(
        f"{API_PREFIX}/stocks/TCS/ohlcv",
        params={"start": "2026-04-01", "end": "2026-01-01"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_refresh_stock(client: AsyncClient) -> None:
    r = await client.post(f"{API_PREFIX}/stocks/TCS/refresh")
    assert r.status_code == 202
    body = r.json()
    assert body["data"]["symbol"] == "TCS"


# ---------------------------- Analysis endpoints ----------------------------


@pytest.mark.asyncio
async def test_get_analysis(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/TCS/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["symbol"] == "TCS"
    assert 0.0 <= body["data"]["score"] <= 1.0
    assert "moving_averages" in body["data"]


@pytest.mark.asyncio
async def test_get_recommendations(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/recommendations", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 5


@pytest.mark.asyncio
async def test_recommendations_history_501(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/recommendations/history")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "NOT_IMPLEMENTED"


# ---------------------------- News endpoints ----------------------------


@pytest.mark.asyncio
async def test_get_news_empty_but_structured(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/TCS/news")
    assert r.status_code == 200
    body = r.json()
    bundle = NewsBundle.model_validate(body["data"])
    assert bundle.symbol == "TCS"
    assert bundle.article_count >= 0


# ---------------------------- Reports endpoints ----------------------------


@pytest.mark.asyncio
async def test_get_report(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/stocks/TCS/report")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["symbol"] == "TCS"
    assert body["data"]["summary"].startswith("Stub report")


@pytest.mark.asyncio
async def test_report_uses_cache(client: AsyncClient) -> None:
    r1 = await client.get(f"{API_PREFIX}/stocks/TCS/report")
    r2 = await client.get(f"{API_PREFIX}/stocks/TCS/report")
    # Both succeed, but the container's stub should only have been called once.
    assert r1.status_code == 200
    assert r2.status_code == 200
    container = client._transport.app.state.container  # type: ignore[attr-defined]
    assert container.llm_service.calls == 1


@pytest.mark.asyncio
async def test_post_report_bypasses_cache(client: AsyncClient) -> None:
    await client.get(f"{API_PREFIX}/stocks/TCS/report")
    r = await client.post(f"{API_PREFIX}/stocks/TCS/report")
    assert r.status_code == 201
    container = client._transport.app.state.container  # type: ignore[attr-defined]
    assert container.llm_service.calls == 2


@pytest.mark.asyncio
async def test_report_503_when_llm_unconfigured(client_no_llm: AsyncClient) -> None:
    r = await client_no_llm.get(f"{API_PREFIX}/stocks/TCS/report")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LLM_UNAVAILABLE"


# ---------------------------- Chat endpoints ----------------------------


@pytest.mark.asyncio
async def test_chat_stream_emits_deltas_and_done(client: AsyncClient) -> None:
    async with client.stream(
        "POST",
        f"{API_PREFIX}/chat/stream",
        json={
            "messages": [{"role": "user", "content": "What's up with TCS?"}],
            "context_symbols": ["TCS"],
        },
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/x-ndjson")
        frames = []
        async for line in r.aiter_lines():
            line = line.strip()
            if line:
                frames.append(line)
    import json as _json

    parsed = [_json.loads(f) for f in frames]
    deltas = [f["delta"] for f in parsed if "delta" in f]
    assert deltas == ["hello ", "world"]
    assert parsed[-1] == {"done": True}

    container = client._transport.app.state.container  # type: ignore[attr-defined]
    sent = container.llm_service.chat_calls[-1]
    assert sent[0].role == "system"
    assert "TCS" in sent[0].content  # context block mentions the symbol
    assert sent[-1].role == "user"


@pytest.mark.asyncio
async def test_chat_stream_503_when_llm_unconfigured(client_no_llm: AsyncClient) -> None:
    r = await client_no_llm.post(
        f"{API_PREFIX}/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}], "context_symbols": []},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_chat_stream_rejects_empty_messages(client: AsyncClient) -> None:
    r = await client.post(
        f"{API_PREFIX}/chat/stream",
        json={"messages": [], "context_symbols": []},
    )
    assert r.status_code == 422


# ---------------------------- Portfolio stubs (Phase 4B) ----------------------------


PORTFOLIO_501_ENDPOINTS = [
    ("GET", "/portfolio/holdings"),
    ("GET", "/portfolio/positions"),
    ("GET", "/portfolio/overview"),
    ("GET", "/portfolio/holdings/TCS"),
    ("GET", "/portfolio/performance"),
    ("GET", "/portfolio/alerts"),
    ("POST", "/portfolio/alerts"),
    ("DELETE", "/portfolio/alerts/some-id"),
    ("GET", "/kite/auth-url"),
    ("POST", "/kite/callback"),
    ("GET", "/kite/status"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", PORTFOLIO_501_ENDPOINTS)
async def test_portfolio_and_kite_endpoints_return_501(
    client: AsyncClient, method: str, path: str
) -> None:
    r = await client.request(method, f"{API_PREFIX}{path}")
    assert r.status_code == 501, f"{method} {path} returned {r.status_code}"
    body = r.json()
    assert body["error"]["code"] == "NOT_IMPLEMENTED"
    assert "meta" in body


# ---------------------------- Watchlist ----------------------------


@pytest.mark.asyncio
async def test_watchlist_add_list_remove_flow(client: AsyncClient) -> None:
    # Initially empty.
    r = await client.get(f"{API_PREFIX}/watchlist")
    assert r.status_code == 200
    assert r.json()["data"] == []

    # Add an entry.
    r = await client.post(
        f"{API_PREFIX}/watchlist",
        json={"symbol": "tcs", "notes": "IT bellwether"},
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["symbol"] == "TCS"
    assert body["notes"] == "IT bellwether"

    # Single-item lookup.
    r = await client.get(f"{API_PREFIX}/watchlist/TCS")
    assert r.status_code == 200
    assert r.json()["data"]["symbol"] == "TCS"

    # List shows it.
    r = await client.get(f"{API_PREFIX}/watchlist")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 1 and items[0]["symbol"] == "TCS"

    # Delete.
    r = await client.delete(f"{API_PREFIX}/watchlist/TCS")
    assert r.status_code == 204

    # Subsequent delete returns 404.
    r = await client.delete(f"{API_PREFIX}/watchlist/TCS")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_get_unknown_returns_404(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/watchlist/UNKNOWN")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_watchlist_post_validation_error(client: AsyncClient) -> None:
    r = await client.post(f"{API_PREFIX}/watchlist", json={"symbol": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_watchlist_analysis_ranked(client: AsyncClient) -> None:
    await client.post(f"{API_PREFIX}/watchlist", json={"symbol": "TCS"})
    r = await client.get(f"{API_PREFIX}/watchlist/analysis/ranked")
    assert r.status_code == 200
    body = r.json()["data"]
    assert isinstance(body, list)
    # TCS is seeded in the fixture so it should have a score.
    assert len(body) >= 1
    assert body[0]["symbol"] == "TCS"


# ---------------------------- Error envelope ----------------------------


@pytest.mark.asyncio
async def test_unknown_route_returns_error_envelope(client: AsyncClient) -> None:
    r = await client.get(f"{API_PREFIX}/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert "meta" in body


@pytest.mark.asyncio
async def test_validation_error_envelope(client: AsyncClient) -> None:
    # limit must be > 0
    r = await client.get(f"{API_PREFIX}/recommendations", params={"limit": 0})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


