# Stock Intelligence System

Personal stock analysis platform for Indian equities (NSE/BSE). Deterministic scoring engine with moving average analysis, news sentiment, and LLM-generated insights — all overlaid on your live Zerodha portfolio.

## What It Does

- **Fetches** daily OHLCV and fundamental data for NSE/BSE stocks
- **Computes** moving averages (SMA 20/50/200, EMA 12/26), crossovers, momentum, volume, and volatility indicators
- **Scores** stocks on a 0-1 scale using configurable weighted metrics
- **Monitors** your Zerodha portfolio via Kite Connect — live P&L, allocation, risk alerts
- **Enriches** with news sentiment and LLM-generated reports (via OpenRouter)
- **Serves** everything through a FastAPI backend and React dashboard

## Architecture

```
React Dashboard  -->  FastAPI API  -->  Processing Engine
                                   -->  Data Layer (Yahoo/Kite)
                                   -->  News Layer (NewsAPI)
                                   -->  LLM Layer (OpenRouter)
                                   -->  Portfolio (Kite Connect)
                                            |
                                        SQLite DB
```

Each layer is a standalone module with abstract interfaces. Swap data providers, LLM models, or sentiment analyzers by changing config — no code changes.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| Frontend | Vite + React 18, TypeScript strict, React Router v6, shadcn/ui, TailwindCSS, Lucide, TanStack Query, Zustand, TradingView Lightweight Charts, Recharts |
| Storage | SQLite (WAL mode) |
| LLM | OpenRouter (any model — Claude, GPT, Llama, Gemini) |
| Broker | Zerodha Kite Connect |
| Data | Yahoo Finance (yfinance) |
| Testing | pytest, hypothesis |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Zerodha Kite Connect API credentials (for portfolio features)
- OpenRouter API key (for LLM reports)

### Setup

```bash
# Clone and enter project
git clone <repo-url>
cd stock_recommendation

# Python backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Initialize database
python scripts/setup_db.py

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# React frontend
cd ui
npm install
```

### Environment Variables

Create a `.env` file in the project root:

```env
KITE_API_KEY=your_kite_api_key
KITE_API_SECRET=your_kite_api_secret
OPENROUTER_API_KEY=your_openrouter_key
```

### Run

```bash
# Terminal 1: API server
uvicorn src.api.app:create_app --factory --reload

# Terminal 2: Vite dev server
cd ui && npm run dev
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:5173

### Backfill Data

```bash
# Fetch 1 year of data for specific stocks
python scripts/backfill.py --symbols RELIANCE,TCS,INFY --days 365

# Run the analysis pipeline
python scripts/run_pipeline.py --symbols RELIANCE,TCS
```

### UI Commands

```bash
cd ui

# First-time setup
npm install

# Dev
npm run dev                    # Vite at http://localhost:5173

# Quality gates
npm run lint
npm run typecheck              # tsc --noEmit
npm run test                   # Vitest (components + hooks)
npm run test:e2e               # Playwright (happy-path flows)

# Production
npm run build                  # vite build → dist/
npm run preview                # preview the production bundle
```

## Key Features

### Moving Average Analysis

Moving averages are a primary metric, not just an internal indicator:

- **SMA(20/50/200)** and **EMA(12/26)** computed for every stock
- **Golden cross / death cross** detection with recency tracking
- **MA alignment** classification: bullish stack, bearish stack, or mixed
- **Price-to-MA distance** as percentage — see how stretched price is from key averages
- **MA slope** direction: rising, falling, or flat
- Interactive chart with toggleable MA overlay lines

### Portfolio Monitoring (Kite Connect)

- Holdings and positions with P&L (on-demand refresh via REST — no live tick feed, personal API key)
- Last price and day P&L come directly from Kite's `/portfolio/holdings` response
- Sector allocation breakdown with concentration warnings
- Analysis score overlay on every holding
- Daily portfolio snapshots with benchmark comparison (Nifty 50)
- Alerts evaluated after the daily EOD pipeline run (score drops, signal changes, volume spikes)

### Deterministic Scoring

Weighted composite score (0 to 1) with configurable weights:

| Metric | Default Weight |
| --- | --- |
| Moving Averages | 25% |
| Momentum | 20% |
| Volume | 15% |
| Volatility | 10% |
| Fundamentals | 20% |
| Support/Resistance | 10% |

All weights and thresholds configurable in `config/processing.yaml`.

### LLM Reports (OpenRouter)

- Structured insights explaining the quantitative analysis
- LLM **augments** — it cannot change scores or select stocks
- Switch models via config: Claude, GPT, Llama, Gemini, etc.
- Automatic fallback chain if primary model is unavailable

## Configuration

All tunables live in `config/*.yaml`:

| File | Controls |
| --- | --- |
| `config/data.yaml` | Data provider, staleness thresholds, backfill settings |
| `config/processing.yaml` | Indicator periods, scoring weights, signal thresholds |
| `config/news.yaml` | News provider, sentiment analyzer, dedup settings |
| `config/llm.yaml` | OpenRouter model, fallback models, token limits |
| `config/api.yaml` | Server host/port, CORS |
| `config/portfolio.yaml` | Kite Connect settings, monitoring intervals, alert rules |

## Testing

```bash
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/ -v                      # Everything
pytest tests/ --cov=src               # With coverage
```

## Project Status

See [PRD.md](PRD.md) for detailed requirements, and [ui/PHASES.md](ui/PHASES.md) for the UI sub-phase plan.

| Phase | Status |
| --- | --- |
| 1. Data Layer | Done |
| 2. Processing Layer | Done |
| 3. News Layer | Done |
| 4. LLM Layer | Done (polish ongoing) |
| 4B. Portfolio & Kite Connect | Deferred (endpoints return 501 until shipped; UI already scaffolded) |
| 5. API Layer | In progress |
| 6. UI Layer | Done — see [ui/PHASES.md](ui/PHASES.md) |

### UI Sub-phases (Phase 6)

Architecture spec: [ui/CLEAN_UI_UX.md](ui/CLEAN_UI_UX.md). Execution plan: [ui/PHASES.md](ui/PHASES.md).

| Sub-phase | Scope | Status |
| --- | --- | --- |
| 6.1 Foundation | Vite scaffold, shadcn/ui, theme, layout shell, API client, shared types | Done |
| 6.2 Stock Browsing | Dashboard top-3, `/stocks` list with search + sector filter, ⌘K command palette | Done |
| 6.3 Stock Detail | Price + volume chart with MA overlays, indicator panel, score breakdown, signal badges, fundamentals | Done |
| 6.4 Intelligence | News feed with sentiment, LLM report cards, generate-fresh flow | Done |
| 6.5 Recommendations | Ranked table, compare mode, pipeline trigger + status | Done |
| 6.6 Portfolio | Holdings table, allocation pie, alerts, Kite connect banner (501-aware) | Done |
| 6.7 Chat | Streaming chat UI with stock-context chip and localStorage persistence | Done |
| 6.8 Polish | Code-splitting, error boundary, settings, a11y, client tests, production build | Done |

## License

Personal project. Not licensed for redistribution.
