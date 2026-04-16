# Stock Intelligence System

## Project Overview

Personal stock intelligence platform for Indian equities (NSE/BSE). Runs locally or on a second machine on the home network. Deterministic scoring core augmented with news sentiment and LLM insights. Integrates with Zerodha Kite Connect for live portfolio monitoring.

See [PRD.md](PRD.md) for full product requirements.

## Tech Stack

- **Language**: Python 3.12+
- **API**: FastAPI + Pydantic v2 + Uvicorn
- **Frontend**: React 18+ (Vite) + React Router + TailwindCSS + TradingView Lightweight Charts
- **Storage**: SQLite (WAL mode) — single file, no external DB needed
- **LLM**: OpenRouter (single API key, routes to any model — Claude, GPT, Llama, Gemini, etc.)
- **Broker**: Zerodha Kite Connect API
- **Testing**: pytest + pytest-asyncio + hypothesis (property tests)
- **Config**: YAML files in `config/`
- **Task scheduling**: APScheduler

## Deployment

- **Personal use only** — no auth, no rate limiting, no public exposure
- Runs on `localhost` or `0.0.0.0` for LAN access from a second machine
- All secrets in `.env` file (gitignored) — no encryption needed for local storage
- SQLite DB file lives in `data/stocks.db` — back up this single file to preserve all data
- Frontend is a plain React SPA served by Vite dev server (or built static files served by FastAPI)

## Project Structure

```text
stock_recommendation/
├── CLAUDE.md                    # This file
├── PRD.md                       # Product requirements
├── pyproject.toml               # Python project config (deps, tools)
├── config/                      # All YAML configuration files
│   ├── data.yaml
│   ├── processing.yaml
│   ├── news.yaml
│   ├── llm.yaml
│   ├── api.yaml
│   └── portfolio.yaml
├── src/
│   ├── __init__.py
│   ├── contracts/               # Shared Pydantic models (inter-module contracts)
│   │   ├── __init__.py
│   │   ├── data.py              # OHLCVRow, Fundamentals, StockInfo
│   │   ├── processing.py        # MovingAverages, Features, StockAnalysis, ScoringConfig
│   │   ├── news.py              # Article, NewsBundle, SentimentResult
│   │   ├── llm.py               # StockReport
│   │   ├── portfolio.py         # Holding, Position, PortfolioOverview
│   │   └── api.py               # APIResponse, APIError wrappers
│   ├── data/                    # Phase 1: Data Layer
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # DataProvider ABC
│   │   │   ├── yahoo.py         # Yahoo Finance implementation
│   │   │   └── kite.py          # Kite Connect data provider
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # StockRepository ABC
│   │   │   └── sqlite.py        # SQLite implementation (WAL mode)
│   │   ├── migrations/          # Schema migrations
│   │   │   └── 001_initial.sql
│   │   └── service.py           # DataService (orchestrates providers + repo)
│   ├── processing/              # Phase 2: Processing Layer
│   │   ├── __init__.py
│   │   ├── indicators/
│   │   │   ├── __init__.py
│   │   │   ├── moving_averages.py # SMA, EMA, crossovers, alignment, slopes
│   │   │   ├── momentum.py      # RSI, returns
│   │   │   ├── volume.py        # Volume ratio, OBV
│   │   │   └── volatility.py    # ATR, std dev
│   │   ├── scoring.py           # Weighted scoring engine
│   │   ├── signals.py           # Signal generation
│   │   └── service.py           # ProcessingService
│   ├── news/                    # Phase 3: News Layer
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # NewsProvider ABC
│   │   │   ├── newsapi.py       # NewsAPI implementation
│   │   │   └── google_rss.py    # Google News RSS fallback
│   │   ├── sentiment/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # SentimentAnalyzer ABC
│   │   │   └── textblob.py      # TextBlob implementation
│   │   ├── dedup.py             # Article deduplication
│   │   └── service.py           # NewsService
│   ├── llm/                     # Phase 4: LLM Layer
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # LLMProvider ABC
│   │   │   └── openrouter.py    # OpenRouter implementation (OpenAI-compatible)
│   │   ├── prompts/
│   │   │   └── stock_report.j2  # Jinja2 prompt template
│   │   └── service.py           # LLMService
│   ├── portfolio/               # Portfolio & Kite Connect
│   │   ├── __init__.py
│   │   ├── kite_client.py       # Kite Connect API wrapper
│   │   ├── monitor.py           # Real-time portfolio monitoring
│   │   ├── analytics.py         # Portfolio analytics (allocation, risk, P&L)
│   │   └── service.py           # PortfolioService
│   ├── api/                     # Phase 5: API Layer
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI application factory
│   │   ├── dependencies.py      # Dependency injection
│   │   ├── middleware.py        # CORS, error handling
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── stocks.py        # /stocks endpoints
│   │       ├── analysis.py      # /analysis, /recommendations
│   │       ├── news.py          # /news endpoints
│   │       ├── reports.py       # /reports (LLM) endpoints
│   │       ├── portfolio.py     # /portfolio endpoints
│   │       └── system.py        # /health, /config, /pipeline
│   ├── scheduler/               # Background job scheduling
│   │   ├── __init__.py
│   │   └── jobs.py              # Scheduled tasks (data refresh, pipeline)
│   └── config.py                # Config loader (YAML → typed objects)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_indicators.py
│   │   ├── test_scoring.py
│   │   ├── test_signals.py
│   │   ├── test_sentiment.py
│   │   ├── test_dedup.py
│   │   └── test_portfolio_analytics.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_data_pipeline.py
│   │   ├── test_processing_pipeline.py
│   │   ├── test_news_pipeline.py
│   │   ├── test_api_endpoints.py
│   │   └── test_portfolio_integration.py
│   └── backtesting/
│       ├── __init__.py
│       └── harness.py           # Backtesting framework
├── scripts/
│   ├── backfill.py              # CLI: backfill historical data
│   ├── run_pipeline.py          # CLI: run full analysis pipeline
│   └── setup_db.py              # CLI: initialize database
├── ui/                          # React SPA (Vite)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx             # Entry point
│   │   ├── App.tsx              # Router setup
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── StockDetail.tsx
│   │   │   ├── Recommendations.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   └── lib/
│   │       └── api-client.ts    # Typed fetch wrappers
│   └── public/
└── data/                        # Runtime data (gitignored)
    └── stocks.db
```

## Coding Standards

### Python

- **Python 3.12+** — use modern syntax (`type` unions `X | None`, `match` statements where appropriate)
- **Type hints on all public functions** — use `typing` for complex types, built-in generics for simple ones
- **Pydantic v2** for all data models — use `BaseModel`, not dataclasses, for anything that crosses module boundaries
- **Abstract base classes** for all swappable components — always define the ABC first, then implement
- **No cross-module imports** — modules import only from `src/contracts/` and their own package
- **Async by default** for I/O-bound operations (API calls, DB queries, HTTP fetches)
- **f-strings** for string formatting (no `.format()` or `%`)
- **pathlib.Path** for all file path operations (no `os.path`)
- **`logging`** module with structured logging — no `print()` statements
- **docstrings** only on public APIs and ABCs — internal functions should be self-documenting via clear naming

### Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_single_leading_underscore`
- Config keys: `snake_case` in YAML

### Configuration

- All tunables live in `config/*.yaml` — never hardcode magic numbers
- Secrets (API keys) go in environment variables, referenced in YAML as `${VAR_NAME}`
- Each module has its own config file
- Config is loaded once at startup and passed via dependency injection

### Error Handling

- Use custom exception classes per module (e.g., `DataFetchError`, `ScoringError`)
- Never catch bare `Exception` — always catch specific types
- Log errors with context (symbol, operation, provider)
- Graceful degradation: if a non-critical module fails, return partial results with a warning

### Testing

- **pytest** as the test runner
- Test files mirror source structure: `src/processing/scoring.py` → `tests/unit/test_scoring.py`
- Fixtures in `conftest.py` — shared test data, mock providers, test DB
- **Unit tests**: pure functions, no I/O, no network
- **Integration tests**: use real SQLite (in-memory), mock external APIs
- **Property tests** (hypothesis): scoring invariants, contract validation
- Test naming: `test_<function>_<scenario>_<expected>` (e.g., `test_compute_rsi_with_insufficient_data_returns_none`)
- Minimum coverage target: 80% on processing layer, 60% overall

### Git

- Branch naming: `phase-N/description` (e.g., `phase-1/data-layer`)
- Commit messages: imperative mood, reference phase (e.g., `[phase-1] add Yahoo Finance data provider`)
- One logical change per commit
- Never commit `data/`, `.env`, or API keys

### Dependencies

- Managed via `pyproject.toml` with dependency groups
- Pin major versions, allow minor updates
- Core deps kept minimal — no unnecessary libraries

## Module Contracts

All inter-module data flows through Pydantic models defined in `src/contracts/`. When adding or modifying a contract:

1. Define the model in the appropriate contracts file
2. Both the producing and consuming modules must use the same model
3. Add validation tests for the contract
4. Update this section if the contract changes materially

## Key Commands

```bash
# Setup
pyenv local 3.13.2
python -m venv venv && source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
python scripts/setup_db.py

# Run
uvicorn src.api.app:create_app --factory --reload     # API server
cd ui && npm run dev                                    # React dev server (Vite)

# Test
pytest tests/unit/                                      # Unit tests only
pytest tests/integration/                               # Integration tests
pytest tests/ -v                                        # All tests
pytest tests/ --cov=src --cov-report=term-missing       # With coverage

# Data
python scripts/backfill.py --symbols RELIANCE,TCS,INFY --days 365
python scripts/run_pipeline.py --symbols RELIANCE,TCS
```
