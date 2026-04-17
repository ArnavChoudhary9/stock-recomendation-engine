# Stock Intelligence System — PRD v2

## 0. Vision

A **modular, deterministic stock intelligence platform** for the Indian equity market. Personal project — runs locally or on a second machine on the home network. The system fetches market and fundamental data, computes quantitative scores, enriches with news sentiment and LLM-generated insights, and exposes everything through APIs and a clean dashboard.

### Core Principles

1. **Deterministic core** — scoring and ranking are pure functions of data; no LLM in the decision path
2. **Layer isolation** — each module communicates through strict typed contracts; no cross-layer imports
3. **Swappable components** — data providers, LLM backends, news sources, and storage engines are behind abstract interfaces
4. **Configuration over code** — weights, thresholds, provider keys, feature flags all live in config files, not hardcoded
5. **Testability first** — every module has unit tests; integration tests validate cross-module contracts

### Design Decisions (changed from v1)

| Area | v1 | v2 | Rationale |
|------|----|----|-----------|
| Storage | SQLite only | **SQLite** (single-file, zero config, perfect for personal use) | No need for PostgreSQL — SQLite handles the scale of personal portfolio + Nifty 500 easily |
| API framework | FastAPI/Flask | **FastAPI** (chosen) | Async-native, auto OpenAPI docs, Pydantic validation |
| Frontend | React/Next.js | **React + Vite** (chosen) | Simple SPA, no SSR needed for personal dashboard, fast dev |
| Config | Implicit | **YAML/TOML config files** per module | Single source of truth for all tunables |
| News sentiment | Basic scoring | **Pluggable analyzers** (TextBlob, FinBERT, LLM) | Different accuracy/cost tradeoffs |
| LLM | Single provider | **OpenRouter** (single API, access to all models) | One API key, model switching via config, no vendor lock-in |
| Scheduling | Cron (vague) | **APScheduler** embedded + optional system cron | Portable, testable, no external dependency |

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        UI Layer                         │
│                   (Next.js Dashboard)                   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│                       API Layer                         │
│                (FastAPI + Pydantic models)              │
└───┬──────────┬──────────┬──────────┬────────────────────┘
    │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌────▼───┐ ┌───▼────┐
│ Data  │ │Process│ │ News   │ │  LLM   │
│ Layer │ │ Layer │ │ Layer  │ │ Layer  │
└───┬───┘ └───┬───┘ └────┬───┘ └───┬────┘
    │         │          │          │
┌───▼─────────▼──────────▼──────────▼────────────────────┐
│                    Storage Layer                        │
│                  (SQLite + WAL mode)                   │
└────────────────────────────────────────────────────────┘
```

### Module Communication Rules

- Modules **never** import from each other directly
- All inter-module communication goes through **typed contracts** (Pydantic models in `src/contracts/`)
- The API layer is the **orchestrator** — it calls modules and composes responses
- Each module exposes a **service class** that implements an abstract interface

---

## 2. Phase 1 — Data Layer

### Objective

Reliable, cached, query-efficient pipeline for Indian equity market data and fundamentals.

### Functional Requirements

#### Market Data (OHLCV)
- Daily OHLCV for NSE/BSE listed stocks
- Volume is critical for scoring
- Support historical backfill (minimum 1 year)
- Incremental daily updates

#### Fundamental Data
- **Required**: PE ratio, market cap, sector, industry
- **Phase 1 optional**: ROE, EPS, debt/equity, promoter holding, dividend yield

#### Data Providers (pluggable)
- **Primary**: Yahoo Finance (`yfinance`) — free, no API key
- **Secondary**: Zerodha Kite Connect — for portfolio holdings/positions (personal key, no live WebSocket feed)
- **Future**: NSE direct feeds, Alpha Vantage

#### Data Freshness
- Scheduled daily update (post market close, ~16:30 IST)
- On-demand fetch for missing/stale data
- Staleness threshold: configurable (default 24h)

### Storage Design

**SQLite with WAL mode** — single file, zero config, ACID compliant. More than sufficient for personal use with Nifty 500 scale data (~500 stocks x 365 days = ~180K rows/year).

```python
class StockRepository(ABC):
    def get_ohlcv(self, symbol: str, start: date, end: date) -> list[OHLCVRow]
    def get_latest_ohlcv(self, symbol: str) -> OHLCVRow | None
    def get_fundamentals(self, symbol: str) -> Fundamentals | None
    def upsert_ohlcv(self, symbol: str, rows: list[OHLCVRow]) -> int
    def upsert_fundamentals(self, symbol: str, data: Fundamentals) -> None
    def list_symbols(self, sector: str | None = None) -> list[StockInfo]
```

#### SQLite Schema

```sql
CREATE TABLE stocks (
    symbol      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    sector      TEXT,
    industry    TEXT,
    exchange    TEXT DEFAULT 'NSE',
    updated_at  TEXT NOT NULL
);

CREATE TABLE ohlcv (
    symbol  TEXT NOT NULL,
    date    TEXT NOT NULL,
    open    REAL NOT NULL,
    high    REAL NOT NULL,
    low     REAL NOT NULL,
    close   REAL NOT NULL,
    volume  INTEGER NOT NULL,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE TABLE fundamentals (
    symbol      TEXT NOT NULL,
    date        TEXT NOT NULL,
    pe          REAL,
    market_cap  REAL,
    roe         REAL,
    eps         REAL,
    debt_equity REAL,
    promoter_holding REAL,
    dividend_yield   REAL,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX idx_ohlcv_date ON ohlcv(date);
CREATE INDEX idx_fundamentals_date ON fundamentals(date);
```

### Data Provider Interface

```python
class DataProvider(ABC):
    def fetch_ohlcv(self, symbol: str, start: date, end: date) -> list[OHLCVRow]
    def fetch_fundamentals(self, symbol: str) -> Fundamentals
    def search_symbol(self, query: str) -> list[StockInfo]
```

### Configuration (`config/data.yaml`)

```yaml
data:
  provider: "yahoo"          # yahoo | kite | alphavantage
  default_exchange: "NSE"
  staleness_threshold_hours: 24
  backfill_days: 365
  batch_size: 50
  rate_limit_delay_ms: 500

storage:
  path: "data/stocks.db"
  wal_mode: true             # better concurrent read performance
```

### Non-Functional Requirements

- Cache persistence across restarts
- Query latency < 50ms for single-stock lookups
- Idempotent upserts (re-running same data is safe)
- Graceful degradation when provider is unavailable

### Deliverables

- [ ] `DataProvider` abstract interface + Yahoo Finance implementation
- [ ] `StockRepository` abstract interface + SQLite implementation
- [ ] Database schema + migrations
- [ ] Daily update scheduler
- [ ] Backfill CLI command
- [ ] Missing data detection and auto-fetch
- [ ] Unit tests for repository and provider
- [ ] Integration test: fetch → store → query round-trip

---

## 3. Phase 2 — Processing Layer

### Objective

Deterministic scoring engine. Given the same input data, it always produces the same output.

### Feature Computation

#### Technical Indicators
- **Moving Averages** (primary metric): SMA(20), SMA(50), SMA(200), EMA(12), EMA(26)
  - MA crossover detection: golden cross (SMA50 crosses above SMA200), death cross (opposite)
  - Price-to-MA distance: how far price is from each MA (% deviation)
  - MA alignment: whether short/medium/long MAs are stacked bullish or bearish
  - MA slope: rising/falling/flat classification for each period
- **Momentum**: RSI(14), 5d return, 10d return, 20d return
- **Volume**: volume ratio (current / 20d avg), OBV
- **Volatility**: ATR(14), standard deviation(20)
- **Support/Resistance**: 52-week high/low proximity

#### Fundamental Scores
- PE relative to sector median
- Market cap tier (large/mid/small)
- ROE ranking within sector

### Scoring Engine

Weighted composite score normalized to [0, 1]:

```python
class ScoringConfig:
    moving_average_weight: float = 0.25   # MA alignment, crossovers, price-to-MA
    momentum_weight: float = 0.20
    volume_weight: float = 0.15
    volatility_weight: float = 0.10
    fundamental_weight: float = 0.20
    support_resistance_weight: float = 0.10
```

Weights are configurable in `config/processing.yaml`. All sub-scores are normalized to [0, 1] before weighting.

**Moving average sub-score** is computed from:
- MA alignment score (bullish stack = 1.0, bearish = 0.0, mixed = 0.5)
- Crossover recency bonus (+0.2 for golden cross in last 5 days, -0.2 for death cross)
- Price-to-SMA(200) distance (closer to or above = higher score)

### Signal Generation

Binary/categorical signals derived from features:

| Signal | Condition |
|--------|-----------|
| `golden_cross` | SMA(50) crosses above SMA(200) in last 5 trading days |
| `death_cross` | SMA(50) crosses below SMA(200) in last 5 trading days |
| `ma_bullish_stack` | price > SMA(20) > SMA(50) > SMA(200), all rising |
| `ma_bearish_stack` | price < SMA(20) < SMA(50) < SMA(200), all falling |
| `price_above_200sma` | price is above SMA(200) |
| `price_below_200sma` | price is below SMA(200) |
| `momentum_strong` | RSI between 50-70, positive 5d return |
| `overbought` | RSI > 70 |
| `oversold` | RSI < 30 |
| `volume_spike` | volume > 2x 20d average |
| `near_52w_high` | within 5% of 52-week high |
| `near_52w_low` | within 5% of 52-week low |

### Output Contract

```python
class MovingAverages(BaseModel):
    sma_20: float
    sma_50: float
    sma_200: float
    ema_12: float
    ema_26: float
    price_to_sma20_pct: float       # % distance from SMA(20)
    price_to_sma50_pct: float
    price_to_sma200_pct: float
    alignment: str                   # "bullish" | "bearish" | "mixed"
    sma50_slope: str                 # "rising" | "falling" | "flat"
    sma200_slope: str
    crossover: str | None            # "golden_cross" | "death_cross" | None
    crossover_days_ago: int | None   # how many days since last crossover

class StockAnalysis(BaseModel):
    symbol: str
    timestamp: datetime
    moving_averages: MovingAverages  # first-class, always present
    features: Features               # momentum, volume, volatility, fundamentals
    score: float                     # 0.0 to 1.0
    signals: dict[str, bool | str]
    metadata: AnalysisMetadata       # config snapshot used
```

### Processing Interface

```python
class ProcessingService(ABC):
    def compute_features(self, symbol: str, ohlcv: list[OHLCVRow], fundamentals: Fundamentals) -> Features
    def compute_score(self, features: Features, config: ScoringConfig) -> float
    def generate_signals(self, features: Features) -> dict[str, bool | str]
    def analyze_stock(self, symbol: str) -> StockAnalysis
    def rank_stocks(self, symbols: list[str]) -> list[StockAnalysis]
```

### Configuration (`config/processing.yaml`)

```yaml
features:
  sma_periods: [20, 50, 200]
  ema_periods: [12, 26]
  rsi_period: 14
  atr_period: 14
  volatility_period: 20
  momentum_periods: [5, 10, 20]
  volume_avg_period: 20

scoring:
  weights:
    moving_average: 0.25
    momentum: 0.20
    volume: 0.15
    volatility: 0.10
    fundamental: 0.20
    support_resistance: 0.10

signals:
  rsi_overbought: 70
  rsi_oversold: 30
  volume_spike_multiplier: 2.0
  near_high_low_pct: 0.05
  crossover_lookback_days: 5        # detect golden/death cross within this window
  ma_slope_period: 10               # days to compute MA slope direction
  ma_slope_flat_threshold: 0.005    # % change below this = "flat"
```

### Testing (mandatory before Phase 3)

- **Unit tests**: each indicator function with known inputs/outputs
- **Property tests**: score always in [0, 1], deterministic on same input
- **Integration test**: full pipeline for a single stock
- **Backtesting harness**: run scoring on historical data, compare scores vs forward returns

### Deliverables

- [ ] Feature computation engine (all technical indicators)
- [ ] Fundamental scoring module
- [ ] Weighted scoring engine with configurable weights
- [ ] Signal generator
- [ ] Output contract validation (Pydantic)
- [ ] Unit tests for every indicator
- [ ] Property-based tests for scoring invariants
- [ ] Backtesting harness CLI
- [ ] Integration test: data layer → processing → validated output

---

## 4. Phase 3 — News Layer

### Objective

Attach recent, relevant, deduplicated news with sentiment scores to each stock.

### Functional Requirements

- Fetch news by ticker symbol and company name
- Configurable time window (default: 72 hours)
- Deduplicate by URL and title similarity
- Sentiment scoring via pluggable analyzers
- Aggregate sentiment per stock

### News Provider Interface

```python
class NewsProvider(ABC):
    def fetch_news(self, query: str, from_date: datetime, to_date: datetime) -> list[RawArticle]
```

Implementations:
- **NewsAPI** (primary) — good coverage, free tier available
- **Google News RSS** (fallback) — no API key needed
- **Future**: Financial-specific feeds (MoneyControl, ET)

### Sentiment Analyzer Interface

```python
class SentimentAnalyzer(ABC):
    def analyze(self, text: str) -> SentimentResult  # score: -1.0 to 1.0
```

Implementations:
- **TextBlob** — fast, free, good enough for v1
- **FinBERT** — finance-tuned, better accuracy, needs GPU
- **LLM-based** — most accurate, highest cost

### Output Contract

```python
class NewsBundle(BaseModel):
    symbol: str
    timestamp: datetime
    articles: list[Article]          # title, summary, source, url, published_at, sentiment
    aggregate_sentiment: float       # -1.0 to 1.0
    article_count: int
    time_window_hours: int
```

### Configuration (`config/news.yaml`)

```yaml
news:
  provider: "newsapi"          # newsapi | google_rss
  time_window_hours: 72
  max_articles_per_stock: 20
  dedup_similarity_threshold: 0.85
  cache_ttl_minutes: 60

sentiment:
  analyzer: "textblob"         # textblob | finbert | llm
  min_text_length: 50
```

### Deliverables

- [ ] `NewsProvider` interface + NewsAPI implementation
- [ ] Google News RSS fallback provider
- [ ] Article deduplication (URL exact match + title fuzzy match)
- [ ] `SentimentAnalyzer` interface + TextBlob implementation
- [ ] Aggregate sentiment computation
- [ ] News caching layer (avoid re-fetching within TTL)
- [ ] Rate limit handling with exponential backoff
- [ ] Unit tests for deduplication and sentiment
- [ ] Integration test: fetch → deduplicate → score → bundle

---

## 5. Phase 4 — LLM Layer

### Objective

Generate structured, human-readable insights that **explain** the quantitative analysis. The LLM **augments** — it does not make decisions.

### Hard Constraints

1. LLM **cannot** modify the quantitative score
2. LLM **cannot** add/remove stocks from recommendations
3. LLM output is **always** structured (not free-form)
4. System works **without** LLM — it's an enhancement, not a dependency

### LLM via OpenRouter

All LLM calls go through **OpenRouter** — a single API that routes to any model (Claude, GPT, Llama, Gemini, etc.). One API key, switch models in config.

```python
class LLMProvider(ABC):
    def generate(self, prompt: str, system: str, schema: type[BaseModel]) -> BaseModel
```

Primary implementation: `OpenRouterProvider` using the OpenAI-compatible API.
Model selection is pure config — no code changes to switch from `anthropic/claude-sonnet-4` to `google/gemini-2.5-flash` to `meta-llama/llama-4-scout`.

### Input Assembly

The LLM receives a structured prompt containing:
- Stock analysis output (score, features, signals)
- News bundle (articles, aggregate sentiment)
- Fundamentals snapshot
- Historical context (30d price action summary)

### Output Contract

```python
class StockReport(BaseModel):
    symbol: str
    timestamp: datetime
    summary: str                     # 2-3 sentence overview
    insights: list[str]              # bullish factors (max 5)
    risks: list[str]                 # risk factors (max 5)
    news_impact: str                 # how news affects outlook
    confidence: float                # 0.0 to 1.0 (LLM self-assessed)
    reasoning_chain: list[str]       # step-by-step reasoning
```

### Configuration (`config/llm.yaml`)

```yaml
llm:
  base_url: "https://openrouter.ai/api/v1"
  api_key: "${OPENROUTER_API_KEY}"
  model: "anthropic/claude-sonnet-4"    # change to any OpenRouter model
  max_tokens: 1024
  temperature: 0.3                       # low for consistent structured output
  max_retries: 3
  timeout_seconds: 30

  # OpenRouter-specific
  fallback_models:                       # auto-fallback if primary model is down
    - "google/gemini-2.5-flash"
    - "meta-llama/llama-4-scout"
```

### Deliverables

- [ ] `LLMProvider` interface + OpenRouter implementation (OpenAI-compatible client)
- [ ] Model fallback chain (try primary, then fallbacks in order)
- [ ] Prompt template system (Jinja2)
- [ ] Structured output parser with validation
- [ ] Retry with exponential backoff
- [ ] Graceful degradation: if all models fail, return report with `summary: "LLM unavailable"`
- [ ] Unit tests for prompt assembly and output parsing
- [ ] Integration test: full input → LLM → validated report

---

## 5.5. Phase 4B — Portfolio & Kite Connect Integration

### Objective

Deep integration with Zerodha Kite Connect for live portfolio monitoring, P&L tracking, and analysis overlay on holdings. This is a **first-class module**, not an afterthought.

### Kite Connect Integration

#### Authentication Flow

1. User visits `/api/v1/kite/auth-url` → gets redirected to Kite login
2. Kite redirects back with `request_token` to `/api/v1/kite/callback`
3. Backend exchanges `request_token` for `access_token` (valid for one trading day)
4. `access_token` stored in encrypted local storage (refreshed daily)

#### Kite API Usage

**Constraint: Personal Kite API key — no WebSocket/live tick streaming, REST-only access.**

| Kite Endpoint | Our Usage | Refresh Frequency |
| --- | --- | --- |
| `/portfolio/holdings` | Holdings, avg buy price, and LTP (Kite includes last_price in response) | On demand (manual refresh) |
| `/portfolio/positions` | Intraday + delivery positions with P&L fields | On demand (manual refresh) |
| `/user/margins` | Available margin, utilization | On demand |
| `/instruments` | Symbol mapping, exchange info | Daily (cache) |

Note: `last_price` in the holdings/positions response from Kite is sufficient for P&L without needing the `/quote` endpoint. No continuous polling — user clicks "Refresh" or navigates to the portfolio page to fetch latest data.

#### Session Management

- Kite access tokens expire at 6:00 AM IST daily
- System detects expired token and prompts re-authentication
- Graceful degradation: if Kite is disconnected, portfolio pages show last-known data with a "stale" badge

### Portfolio Monitoring Features

#### On-Demand P&L Dashboard
- **Holdings P&L**: (last_price - avg_buy_price) * quantity for each holding
- **Day P&L**: (last_price - previous_close) * quantity (from Kite holdings response)
- **Positions P&L**: profit/loss at last fetched price (no live tick)
- **Total portfolio value**: sum of all holdings at last fetched price
- Data refreshes only when user clicks "Refresh" or reloads the portfolio page (no background polling)

#### Portfolio Analytics
- **Allocation breakdown**: by sector, market cap tier, and individual stock weight
- **Concentration risk**: flag if any single stock > 15% of portfolio, or single sector > 40%
- **Score overlay**: map each holding to its analysis score — highlight holdings with declining scores
- **Divergence alerts**: holding has a low score (< 0.3) but large allocation

#### Performance Tracking
- Daily portfolio value snapshots (stored in DB)
- Time-series performance chart (1W, 1M, 3M, 6M, 1Y, ALL)
- Benchmark comparison (Nifty 50, Nifty 500)
- XIRR calculation for true returns

#### Alert System
- **Score drop alert**: stock score drops below configurable threshold
- **Signal change alert**: key signal flips (bullish → bearish)
- **Volume spike alert**: unusual volume on a held stock
- **News sentiment alert**: negative sentiment spike on a held stock
- Alert delivery: in-app notification (v1), optional webhook/email (future)

### Portfolio Contracts

```python
class Holding(BaseModel):
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    pnl_pct: float
    day_change: float
    day_change_pct: float

class Position(BaseModel):
    symbol: str
    exchange: str
    product: str               # CNC, MIS, NRML
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    buy_quantity: int
    sell_quantity: int

class PortfolioOverview(BaseModel):
    total_investment: float
    current_value: float
    total_pnl: float
    total_pnl_pct: float
    day_pnl: float
    holdings: list[Holding]
    positions: list[Position]
    allocation_by_sector: dict[str, float]
    concentration_warnings: list[str]
    score_overlay: dict[str, float]  # symbol → analysis score

class PortfolioSnapshot(BaseModel):
    date: date
    total_value: float
    invested_value: float
    holdings_count: int

class AlertRule(BaseModel):
    id: str
    type: str                  # score_drop, signal_change, volume_spike, sentiment
    symbol: str | None         # None = all holdings
    threshold: float
    enabled: bool

class Alert(BaseModel):
    id: str
    rule_id: str
    symbol: str
    message: str
    timestamp: datetime
    acknowledged: bool
```

### Kite Client Interface

```python
class KiteClient(ABC):
    async def get_holdings(self) -> list[Holding]      # includes last_price + day P&L
    async def get_positions(self) -> list[Position]    # includes last_price + P&L
    async def get_margins(self) -> dict
    async def get_instruments(self, exchange: str) -> list[Instrument]
    def is_authenticated(self) -> bool
    def get_auth_url(self) -> str
    async def generate_session(self, request_token: str) -> str
```

### Configuration (`config/portfolio.yaml`)

```yaml
portfolio:
  snapshot_enabled: true
  snapshot_time: "16:30"            # IST, after market close

kite:
  api_key: "${KITE_API_KEY}"
  api_secret: "${KITE_API_SECRET}"
  redirect_url: "http://localhost:8000/api/v1/kite/callback"
  token_path: "data/.kite_token"    # plain file, local-only — no encryption needed

monitoring:
  # Personal Kite key — no live WebSocket feed. Data refreshes on-demand.
  cache_ttl_seconds: 60             # dedupe rapid manual refreshes within this window
  market_hours:
    open: "09:15"
    close: "15:30"
    timezone: "Asia/Kolkata"

alerts:
  enabled: true
  score_drop_threshold: 0.3
  volume_spike_multiplier: 3.0
  sentiment_drop_threshold: -0.5
  # Alerts evaluated after the daily EOD pipeline run, not continuously
  run_after_pipeline: true
```

### Storage (additional tables)

```sql
CREATE TABLE portfolio_snapshots (
    date        TEXT NOT NULL,
    total_value REAL NOT NULL,
    invested    REAL NOT NULL,
    holdings    INTEGER NOT NULL,
    PRIMARY KEY (date)
);

CREATE TABLE alert_rules (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    symbol      TEXT,
    threshold   REAL NOT NULL,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE alerts (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    message     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    acknowledged INTEGER DEFAULT 0,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
);
```

### Deliverables

- [ ] `KiteClient` abstract interface + Kite Connect implementation
- [ ] Mock Kite client for testing (returns fixture data)
- [ ] OAuth flow: auth URL → callback → token storage (plain file)
- [ ] Session expiry detection and re-auth prompt
- [ ] Holdings and positions fetching with live P&L
- [ ] Portfolio analytics (allocation, concentration, XIRR)
- [ ] Score overlay on holdings
- [ ] Daily portfolio snapshot scheduler
- [ ] Performance time-series with benchmark comparison
- [ ] Alert rule CRUD
- [ ] Alert checker (runs on schedule, evaluates rules)
- [ ] Unit tests for analytics calculations
- [ ] Integration test: mock Kite → portfolio overview → alert evaluation

---

## 6. Phase 5 — API Layer

### Objective

RESTful API that orchestrates all modules and exposes them with consistent contracts.

### Technology

- **FastAPI** with async support
- **Pydantic v2** for request/response models
- Auto-generated **OpenAPI/Swagger** docs

### Endpoints

#### Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stocks` | List all tracked stocks (filterable by sector) |
| GET | `/api/v1/stocks/{symbol}` | Stock info + latest fundamentals |
| GET | `/api/v1/stocks/{symbol}/ohlcv` | OHLCV time series (query params: start, end) |
| POST | `/api/v1/stocks/{symbol}/refresh` | Trigger data refresh for a stock |

#### Analysis
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stocks/{symbol}/analysis` | Full analysis (features, score, signals) |
| GET | `/api/v1/recommendations` | Top N ranked stocks (query param: limit, sector) |
| GET | `/api/v1/recommendations/history` | Historical recommendation snapshots |

#### News
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stocks/{symbol}/news` | News bundle with sentiment |

#### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stocks/{symbol}/report` | LLM-generated report |
| POST | `/api/v1/stocks/{symbol}/report` | Generate fresh report (bypasses cache) |

#### Portfolio & Kite Connect
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/portfolio/holdings` | Current holdings with live P&L |
| GET | `/api/v1/portfolio/positions` | Open positions (intraday + delivery) |
| GET | `/api/v1/portfolio/overview` | Portfolio summary: allocation, risk, total P&L |
| GET | `/api/v1/portfolio/holdings/{symbol}` | Single holding detail + analysis overlay |
| GET | `/api/v1/portfolio/performance` | Time-series portfolio value (daily snapshots) |
| GET | `/api/v1/portfolio/alerts` | Active alerts (score drops, signal changes) |
| POST | `/api/v1/portfolio/alerts` | Create alert rule |
| DELETE | `/api/v1/portfolio/alerts/{id}` | Remove alert rule |
| GET | `/api/v1/kite/auth-url` | Get Kite Connect login URL |
| POST | `/api/v1/kite/callback` | Handle Kite OAuth callback, store access token |
| GET | `/api/v1/kite/status` | Check if Kite session is active |

#### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/config` | Current active configuration (non-sensitive) |
| POST | `/api/v1/pipeline/run` | Trigger full pipeline run |

### API Design Rules

- All responses wrapped in `{ "data": ..., "meta": { "timestamp": ..., "version": ... } }`
- Errors use `{ "error": { "code": "...", "message": "..." } }`
- Versioned routes (`/api/v1/`)
- No auth needed — personal use, local/LAN only. Bind to `127.0.0.1` by default (or `0.0.0.0` if accessing from second machine)
- CORS open for local development

### Configuration (`config/api.yaml`)

```yaml
api:
  host: "127.0.0.1"              # change to 0.0.0.0 for LAN access
  port: 8000
  cors:
    allowed_origins: ["*"]        # personal use, no restriction needed

kite:
  api_key: "${KITE_API_KEY}"
  api_secret: "${KITE_API_SECRET}"
```

### Deliverables

- [ ] FastAPI application with router structure
- [ ] Pydantic request/response models (matching layer contracts)
- [ ] Dependency injection for services
- [ ] CORS configuration
- [ ] Health check endpoint
- [ ] Kite Connect integration for portfolio
- [ ] OpenAPI documentation auto-generated
- [ ] Error handling middleware (consistent error format)
- [ ] Integration tests for all endpoints

---

## 7. Phase 6 — UI Layer

### Objective

Clean, fast dashboard for viewing recommendations, analyzing stocks, and monitoring portfolio.

### Technology

- **React 18+** with Vite (fast builds, simple SPA)
- **React Router** for client-side routing
- **TailwindCSS** for styling
- **Lightweight Charts** (TradingView) for candlestick/line charts
- **TanStack Query** for data fetching and caching
- No auth — open access, personal use only

### Pages

#### Dashboard (`/`)
- Top 5 recommendations with scores and key signals
- Market overview (Nifty 50, sector performance)
- Recent pipeline run status
- Quick search bar

#### Stock Detail (`/stocks/:symbol`)
- Interactive candlestick chart with **SMA(20/50/200) overlay lines** (toggleable)
- Moving averages panel: current values, alignment status, crossover badge, price-to-MA distances
- Technical indicators panel (RSI, volume)
- Score breakdown (radar chart or bar chart) — MA score shown as its own wedge
- Signal badges (golden cross / death cross highlighted prominently)
- News feed with sentiment indicators
- LLM report card (collapsible)
- Fundamental data table

#### Recommendations (`/recommendations`)
- Sortable, filterable table of all analyzed stocks
- Score, sector, key signals, sentiment
- Compare mode (select 2-3 stocks side by side)

#### Portfolio (`/portfolio`)
- Holdings table with current P&L
- Allocation pie chart
- Per-holding analysis overlay (score, signals)
- Risk summary

#### Settings (`/settings`)
- Scoring weight sliders
- Provider configuration
- Pipeline schedule control

### UX Requirements

- Page load < 1s, API responses < 300ms
- Desktop primary (responsive is nice-to-have)
- Dark mode support
- Loading skeletons (no layout shift)

### Deliverables

- [ ] React + Vite project setup with TailwindCSS
- [ ] React Router with route structure
- [ ] Dashboard page
- [ ] Stock detail page with interactive charts
- [ ] Recommendations page with sorting/filtering
- [ ] Portfolio page
- [ ] Settings page
- [ ] API client layer (typed fetch wrappers)
- [ ] Dark mode
- [ ] Error and empty states

---

## 8. Phase Dependencies and Execution Order

```
Phase 1: Data Layer ──────────────────────┐
                                          │
Phase 2: Processing Layer ────────────────┤
     (depends on Phase 1)                 │
                                          ├──→ Phase 5: API Layer ──→ Phase 6: UI Layer
Phase 3: News Layer ──────────────────────┤    (depends on 1-4B)       (depends on 5)
     (parallel with Phase 2)              │
                                          │
Phase 4: LLM Layer ──────────────────────┤
     (depends on Phase 2 + 3)             │
                                          │
Phase 4B: Portfolio & Kite Connect ───────┘
     (depends on Phase 1 + 2)
```

**Parallelization opportunities:**

- Phase 3 (News) can run in parallel with Phase 2 (Processing)
- Phase 4B (Portfolio) can run in parallel with Phase 3 + 4 (needs only Phase 1 + 2)
- UI component development can start during Phase 5 with mock data

### Milestone Summary

| Phase | Core Deliverable | Done When |
| --- | --- | --- |
| 1 | Data pipeline fetches and stores OHLCV + fundamentals | Can query 1 year of data for any Nifty 50 stock |
| 2 | Scoring engine produces deterministic scores | Backtesting harness runs, all tests pass |
| 3 | News pipeline attaches sentiment to stocks | News bundle generated for any stock with sentiment |
| 4 | LLM generates structured reports | Report generated for any stock, validates against schema |
| 4B | Portfolio monitoring with Kite Connect | Holdings fetched, P&L calculated, alerts firing |
| 5 | API exposes all functionality | All endpoints return correct data, Swagger docs live |
| 6 | Dashboard displays recommendations + portfolio | User can view analysis, portfolio, and drill into stocks |

---

## 9. MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 4B (Kite) + minimal Phase 5**

This gives you:

1. Data fetching and storage for NSE stocks
2. Deterministic scoring and ranking
3. Kite Connect integration with live holdings and P&L
4. API endpoints: `/recommendations` + `/portfolio/overview`

**Post-MVP additions (in order):**

1. News layer (sentiment enrichment)
2. LLM layer (human-readable reports)
3. Full API surface + alert system
4. UI dashboard
5. Performance tracking + benchmarking

---

## 10. Future Extensions

- Real-time streaming via Kite WebSocket (requires upgraded API subscription — not available on personal key)
- Portfolio optimization (Markowitz, risk parity)
- Sector rotation models
- Options chain analysis
- Order placement via Kite Connect (with confirmation safeguards)
- Multi-market support (US equities)
- Mobile app (React Native, sharing Next.js logic)
- Reinforcement learning for weight optimization
- Tax-loss harvesting suggestions based on holdings P&L
