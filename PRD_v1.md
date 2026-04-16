Below is a **phased PRD (Product Requirements Document)** aligned with your architecture and constraints (modular, swappable layers, deterministic core, LLM as augmentation).

---

# 0. Product Overview

**Goal**
Build a modular stock intelligence system that:

* Fetches + caches market + fundamentals
* Computes deterministic scores
* Augments with news + LLM insights
* Exposes everything via APIs + UI

**Key Design Principles**

* Layer isolation (strict contracts)
* Deterministic core (processing layer)
* Replaceable components (LLM, data providers)
* Persistent + query-efficient storage

---

# Phase 1 — Data Layer

## Objective

Reliable, persistent, and query-efficient market + fundamental data pipeline.

---

## Functional Requirements

### 1. Market Data

* OHLCV (daily mandatory, intraday optional later)
* Volume (critical)
* Corporate actions (optional future)

### 2. Fundamental Data

* PE ratio
* Market cap
* Sector
* Optional:

  * ROE, EPS, Debt/Equity

### 3. Data Freshness

* Daily update job (cron)
* On-demand fetch for missing data
* Backfill support (user provides 1-year data)

---

## Storage Design

### Choice: SQLite (B-tree backed)

* Built-in indexing (B-tree)
* ACID compliance
* Easy integration

### Schema (suggested)

```sql
stocks(symbol PRIMARY KEY, name, sector)

ohlcv(
  symbol,
  date,
  open, high, low, close,
  volume,
  PRIMARY KEY(symbol, date)
)

fundamentals(
  symbol,
  date,
  pe,
  market_cap,
  roe,
  PRIMARY KEY(symbol, date)
)
```

---

## Interfaces (IMPORTANT)

```python
get_ohlcv(symbol, start, end) -> DataFrame
get_latest_ohlcv(symbol) -> Row
get_fundamentals(symbol) -> Dict
update_symbol(symbol) -> None
```

---

## Non-Functional Requirements

* Cache persistence across restarts
* Query latency < 50ms
* Idempotent updates

---

## Checklist

* [ ] Data ingestion pipeline
* [ ] SQLite schema + indexing
* [ ] Backfill loader (1-year data)
* [ ] Incremental updater
* [ ] Missing data handler
* [ ] Provider abstraction (Zerodha / Yahoo)

---

# Phase 2 — Processing Layer

## Objective

Deterministic scoring engine with strict output contracts.

---

## Functional Requirements

### 1. Feature Computation

* Moving averages (20, 50, 200)
* Momentum (5d, 10d returns)
* Volume ratios
* Volatility

### 2. Scoring Engine

* Weighted scoring model
* Configurable weights

---

## Output Contract (CRITICAL)

All outputs must follow a fixed schema:

```json
{
  "symbol": "TCS",
  "features": {
    "trend": 0.8,
    "momentum": 0.6,
    "volume": 0.7,
    "volatility": 0.2
  },
  "score": 0.74,
  "signals": {
    "trend_signal": "bullish",
    "volume_spike": true
  }
}
```

---

## Interfaces

```python
compute_features(symbol, data) -> FeaturesDict
compute_score(features) -> float
generate_signals(features) -> Dict
process_stock(symbol) -> StandardOutput
```

---

## Testing Sub-Phase (MANDATORY)

### Goals

* Ensure correctness + stability
* Enable safe refactoring

### Tests

#### Unit Tests

* Indicator correctness
* Edge cases (missing data)

#### Integration Tests

* End-to-end processing for 1 stock

#### Backtesting Harness

* Input: historical data
* Output:

  * score vs returns
  * performance metrics

---

## Checklist

* [ ] Feature engine
* [ ] Scoring module
* [ ] Signal generator
* [ ] Output schema validator
* [ ] Unit tests
* [ ] Backtesting tool

---

# Phase 3 — News Layer

## Objective

Attach relevant, recent news to each stock.

---

## Functional Requirements

* Fetch news by ticker/company name
* Time window: last 24–72 hours
* Deduplicate articles
* Basic sentiment scoring

---

## Output Contract

```json
{
  "symbol": "TCS",
  "articles": [
    {
      "title": "...",
      "summary": "...",
      "source": "...",
      "timestamp": "...",
      "sentiment": 0.5
    }
  ],
  "aggregate_sentiment": 0.42
}
```

---

## Interfaces

```python
get_news(symbol) -> NewsBundle
summarize_news(articles) -> List
compute_sentiment(articles) -> float
```

---

## Checklist

* [ ] News fetcher (NewsAPI / scraping)
* [ ] Deduplication logic
* [ ] Summarizer
* [ ] Sentiment scorer
* [ ] Rate limit handling

---

# Phase 4 — LLM Layer

## Objective

Generate structured insights (NOT decisions).

---

## Input

* Processing output
* News summary
* Fundamentals

---

## Output Contract

```json
{
  "symbol": "TCS",
  "summary": "...",
  "insights": [
    "Strong uptrend supported by volume",
    "Positive sentiment from earnings news"
  ],
  "risks": [
    "Overbought RSI"
  ],
  "confidence": 0.78
}
```

---

## Constraints

* LLM cannot change score
* LLM cannot select stocks
* Only explanation + reasoning

---

## Interfaces

```python
generate_report(stock_data) -> Report
```

---

## Checklist

* [ ] Prompt template
* [ ] Structured output parser
* [ ] Retry + fallback
* [ ] Cost control (token limits)

---

# Phase 5 — API Layer

## Objective

Expose system functionality via clean APIs.

---

## Core Endpoints

### Data

* `GET /stocks`
* `GET /stocks/{symbol}/ohlcv`
* `GET /stocks/{symbol}/fundamentals`

### Processing

* `GET /stocks/{symbol}/analysis`
* `GET /recommendations`

### News

* `GET /stocks/{symbol}/news`

### LLM

* `GET /stocks/{symbol}/report`

### Portfolio (Zerodha)

* Integrate Zerodha Kite Connect
* `GET /portfolio`
* `GET /holdings`
* `GET /positions`

---

## Chart Data

* `GET /stocks/{symbol}/chart`

  * returns full OHLCV time series

---

## Design Constraints

* Stateless APIs
* JSON contracts consistent with internal layers
* Rate limiting

---

## Checklist

* [ ] FastAPI/Flask server
* [ ] Route definitions
* [ ] Auth (API keys)
* [ ] Kite Connect integration
* [ ] Response schema validation

---

# Phase 6 — UI Layer

## Objective

Unified interface for analysis, portfolio, and recommendations.

---

## Core Features

### Dashboard

* Top recommendations (Top 3)
* Market overview

### Stock View

* Price chart
* Technical indicators
* News + sentiment
* LLM report

### Portfolio View

* Holdings (via Zerodha)
* Allocation visualization
* Risk metrics

### Recommendation Engine

* Run pipeline on demand
* Show ranked stocks

---

## Suggested Stack

* Frontend: React / Next.js
* Charts: TradingView / lightweight charts
* Backend: API layer

---

## UX Requirements

* Fast (<300ms API latency)
* Clean, minimal UI
* Drill-down capability

---

## Checklist

* [ ] Dashboard page
* [ ] Stock detail page
* [ ] Portfolio page
* [ ] Chart integration
* [ ] API integration

---

# Phase Dependencies

```id="t3kkv4"
Data → Processing → News → LLM
          ↓
         API → UI
```

---

# MVP Scope (Strict)

Start with:

1. Data layer (SQLite + OHLCV)
2. Processing layer (basic scoring)
3. API (`/recommendations`)
4. Minimal UI (table + scores)

Then add:

* News
* LLM
* Portfolio integration

---

# Future Extensions

* Real-time streaming
* Portfolio optimization engine
* Reinforcement learning for weights
* Sector rotation models
