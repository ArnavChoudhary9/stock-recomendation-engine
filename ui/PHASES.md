# UI Phase Plan (Phase 6)

This document is the execution plan for the frontend. It refines [CLEAN_UI_UX.md](CLEAN_UI_UX.md) (architecture spec) and [../PRD.md](../PRD.md) §7 (Phase 6 requirements) into concrete, shippable sub-phases.

**Tech stack (per CLEAN_UI_UX.md):**
- Vite + React 18+ · TypeScript (strict) · React Router v6
- shadcn/ui · Tailwind CSS · Lucide icons
- TanStack Query (server state) · Zustand (client state)
- TradingView Lightweight Charts (price) · Recharts (other charts)
- React Hook Form + Zod · streaming chat via fetch + `ReadableStream` (or `ai` SDK — framework-agnostic)
- Vitest + React Testing Library · Playwright (E2E)

> **Why Vite (not Next.js):** personal local-LAN SPA. No SSR/SEO need, no Node runtime at the edge, no server components. Vite gives faster HMR, a tiny static build served directly by FastAPI in prod, and a simpler mental model.

---

## Target folder structure

```
ui/
├── CLEAN_UI_UX.md              # UI architecture spec (source of truth)
├── PHASES.md                   # This file
├── index.html                  # Vite entry HTML
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── components.json             # shadcn/ui config
├── public/
└── src/
    ├── main.tsx                # Entry: providers tree + <RouterProvider/>
    ├── router.tsx              # React Router route definitions
    ├── routes/                 # Route components (one per page)
    │   ├── Dashboard.tsx       # /
    │   ├── Stocks.tsx          # /stocks
    │   ├── StockDetail.tsx     # /stocks/:symbol
    │   ├── Recommendations.tsx # /recommendations
    │   ├── Portfolio.tsx       # /portfolio
    │   ├── Alerts.tsx          # /portfolio/alerts
    │   ├── Chat.tsx            # /chat
    │   └── Settings.tsx        # /settings
    │
    ├── components/
    │   ├── ui/                 # shadcn primitives (Button, Card, Table, Dialog, Tabs, …)
    │   ├── shared/             # PageHeader, EmptyState, ErrorBoundary, Skeletons
    │   ├── layout/             # AppShell, Sidebar, TopBar, Breadcrumbs
    │   ├── charts/             # PriceChart, ScoreRadar, AllocationPie, SparklineCell
    │   ├── stock/              # StockCard, SignalBadges, IndicatorPanel, FundamentalsTable
    │   └── portfolio/          # HoldingRow, AllocationBreakdown, AlertCard
    │
    ├── features/               # Domain feature slices (hooks + feature-specific UI glue)
    │   ├── stocks/             # useStocks, useStock, useOhlcv, useAnalysis
    │   ├── recommendation/     # useRecommendations, useTriggerPipeline
    │   ├── news/               # useStockNews
    │   ├── report/             # useStockReport, useGenerateReport
    │   ├── portfolio/          # usePortfolioOverview, useHoldings, useAlerts, useKiteAuth
    │   └── chat/               # useChatStream, chat store wiring
    │
    ├── lib/
    │   ├── api/                # Centralized API client + envelope unwrapping
    │   │   ├── client.ts       # fetch wrapper, typed, handles APIResponse/APIError
    │   │   ├── endpoints.ts    # Route constants
    │   │   └── errors.ts
    │   ├── hooks/              # Generic hooks (useDebounce, useMediaQuery)
    │   ├── utils/              # formatters, classnames (cn), date helpers
    │   └── types/              # Shared TS types mirroring src/contracts/*
    │
    ├── store/                  # Zustand stores (UI prefs, chat context, filters)
    └── styles/                 # globals.css, Tailwind tokens
```

**Why this layout:**
- `components/` holds *visual* primitives; `features/` holds *domain* logic (hooks, feature shells). A `StockCard` doesn't know about React Query; a `useStock()` hook doesn't know about pixels.
- `lib/api/` is the single place that talks to FastAPI. UI components never call `fetch`.
- `lib/types/` mirrors `src/contracts/` — hand-written initially, candidate for codegen later.
- `store/` is reserved for cross-feature client state only (theme, chat context, active filters). Server state lives in React Query.
- `routes/` holds page-level components; `router.tsx` is the single place routes are declared.

---

## Global principles

1. **No fetch in components.** All I/O through `lib/api/client.ts`, wrapped by a feature hook.
2. **One envelope shape.** Backend returns `{ data, meta }` or `{ error }` — `client.ts` unwraps to `data` or throws typed errors.
3. **Strong types everywhere.** `lib/types/` mirrors `src/contracts/*.py`. When the backend changes a contract, TS types change in lockstep.
4. **shadcn first.** No custom Button/Card/Dialog. Extend via composition, not forks.
5. **Skeletons not spinners.** Every async surface ships a skeleton matching its final layout.
6. **Graceful 501.** Portfolio endpoints return 501 until Phase 4B ships — UI must render an informative "coming soon" state, not an error toast.
7. **Dark mode from day one.** Theme tokens in Tailwind; no hard-coded hex.

---

## Phase 6.1 — Foundation & Design System

**Goal:** a running Vite + React app with layout, theme, API client, and one live data call to prove the wiring.

**Deliverables**
- [ ] Vite + React 18 + TypeScript scaffold (`npm create vite@latest ui -- --template react-ts`), strict TS, ESLint + Prettier
- [ ] React Router v6 with route definitions in `src/router.tsx`
- [ ] Tailwind + shadcn init (`components.json`), install core primitives: Button, Card, Input, Dialog, Tabs, Table, Skeleton, Tooltip, Badge, Sheet, DropdownMenu, Command
- [ ] Theme tokens (colors, spacing, typography scale) in `tailwind.config.ts` + `src/styles/globals.css`
- [ ] Light/dark mode via a simple `ThemeProvider` (Zustand-backed or `localStorage`)
- [ ] App shell: `Sidebar` + `TopBar` + content outlet (responsive, desktop-first)
- [ ] Providers tree: React Query (with devtools in dev), ThemeProvider, RouterProvider, Zustand stores mounted as needed
- [ ] `lib/api/client.ts` — typed fetch, envelope unwrapping, `APIError` class; reads `VITE_API_BASE_URL` from env (defaults to `http://localhost:8000`)
- [ ] Vite proxy config so `/api/*` forwards to FastAPI in dev (avoids CORS during development)
- [ ] `lib/types/` — hand-written TS for `StockInfo`, `OHLCVRow`, `StockAnalysis`, `NewsBundle`, `StockReport`, `PortfolioOverview`, `APIResponse<T>`, `APIError`
- [ ] Health check wired: dashboard renders API status pill (green = `/api/v1/health` ok, red = down)
- [ ] Shared components: `PageHeader`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `StatCard`

**Exit criteria**
- `npm run dev` serves the app at `localhost:5173`
- `/` renders the shell with a working theme toggle and a live health-check pill

---

## Phase 6.2 — Stock Browsing

**Goal:** discover and search stocks; the dashboard shows real top recommendations.

**Deliverables**
- [ ] Hooks: `useStocks(filter)`, `useStock(symbol)` backed by `/api/v1/stocks`
- [ ] `/stocks` route: searchable, sector-filterable table with sort (symbol, sector, last_close, score)
- [ ] `StockCard` component with score ring, sparkline, signal badges
- [ ] Dashboard (`/`): Top 3 recommendation cards (via `/api/v1/recommendations?limit=3`), market overview placeholder, quick search in TopBar
- [ ] Global command palette (`⌘K` / `Ctrl+K`) using shadcn `Command` — jump to any stock
- [ ] Skeletons for table rows and cards
- [ ] URL-synced filters (React Router search params) so deep links work

**Exit criteria**
- User can search, filter by sector, click into any stock
- Dashboard top-3 matches what `/recommendations` returns

---

## Phase 6.3 — Stock Detail (chart, indicators, score)

**Goal:** the signature page — a stock's full quantitative picture.

**Deliverables**
- [ ] `/stocks/:symbol` route with tabs: Overview / News / Report / Fundamentals
- [ ] `PriceChart` (TradingView Lightweight Charts): candlestick + toggleable overlays for SMA(20/50/200) and EMA(12/26)
- [ ] MA panel: current MA values, alignment (bullish/bearish/mixed) badge, golden/death-cross badge with "N days ago", price-to-MA distances, slope direction
- [ ] `IndicatorPanel`: RSI gauge, volume bars, ATR / volatility number
- [ ] `ScoreBreakdown`: Recharts radial or horizontal bar showing the 6 weighted sub-scores; total score prominent
- [ ] `SignalBadges` row: prominent styling for golden_cross / death_cross, subdued for others
- [ ] `FundamentalsTable`: PE, market cap, ROE, EPS, debt/equity, dividend yield
- [ ] Refresh button → `POST /stocks/:symbol/refresh` with optimistic toast

**Exit criteria**
- Any symbol with data renders the full page in < 1s after navigation (cached)
- MA overlays toggle without refetching
- Score breakdown numbers match `StockAnalysis.score` exactly

---

## Phase 6.4 — Intelligence (News + LLM Reports)

**Goal:** human-readable context — why the score moved.

**Deliverables**
- [ ] News tab: article list with title, source, timestamp, sentiment pill (−1..+1 colour-coded), aggregate sentiment meter at top
- [ ] Sentiment time window selector (24h / 72h / 7d)
- [ ] `useStockNews(symbol, windowHours)` hook
- [ ] Report tab: rendered `StockReport` — summary, insights list, risks list, news_impact, confidence meter, reasoning chain (collapsible)
- [ ] "Generate fresh report" button → `POST /stocks/:symbol/report` with loading state
- [ ] Markdown rendering for LLM text blocks (safe: no raw HTML)
- [ ] Graceful degradation card when `summary == "LLM unavailable"`

**Exit criteria**
- News renders with correct sentiment colors; aggregate matches backend
- Report generation shows progress and updates in place on success

---

## Phase 6.5 — Recommendations & Pipeline

**Goal:** power-user workflow — rank, filter, compare, and trigger runs.

**Deliverables**
- [ ] `/recommendations` route: full ranked table (symbol, score, sector, key signals, sentiment, day change)
- [ ] Sort by any column, multi-select sector filter, score range slider
- [ ] Compare mode: select 2–3 rows → side-by-side drawer with score breakdown and signals
- [ ] Pipeline trigger: button opens dialog (symbols multi-select or "all tracked"), calls `POST /pipeline/run`, polls for status
- [ ] Last-run indicator in TopBar (timestamp + status)
- [ ] `useRecommendations`, `useTriggerPipeline`, `usePipelineStatus` hooks
- [ ] Historical snapshots view (`/recommendations/history`) — simple date-picker + table

**Exit criteria**
- Triggering a pipeline run updates the last-run pill and refetches recommendations on completion
- Compare drawer can hold 3 stocks and renders without layout shift

---

## Phase 6.6 — Portfolio & Kite (gated on Phase 4B)

**Goal:** holdings overlaid with the scoring engine's view.

> **Until Phase 4B ships,** portfolio endpoints return HTTP 501. The UI must render a first-class "Connect Kite — not yet available" empty state, not an error toast. When 4B lands, only the hooks change; the layout is ready.

**Deliverables**
- [ ] `/portfolio` route: holdings table (symbol, qty, avg, LTP, P&L ₹ + %, day change, **score overlay**, key signals)
- [ ] Allocation pie (by sector) + concentration warnings banner
- [ ] Portfolio summary: total invested, current value, total P&L, day P&L
- [ ] Performance chart (daily snapshots) with Nifty 50 benchmark overlay — 1W/1M/3M/6M/1Y/ALL toggle
- [ ] Alerts route: list of active alerts, acknowledge action, rule CRUD dialog
- [ ] Kite auth flow: "Connect Kite" button → `/api/v1/kite/auth-url` → Kite login → callback → status pill
- [ ] Session expiry banner + re-auth prompt
- [ ] `usePortfolioOverview`, `useHoldings`, `useAlerts`, `useKiteStatus`, `useKiteAuthUrl`

**Exit criteria**
- With a connected Kite session and seeded data, `/portfolio` renders P&L matching Kite web
- With no session, page shows the connect CTA — never a crash or unstyled error

---

## Phase 6.7 — Chat Interface

**Goal:** conversational exploration with stock context injection.

> **Dependency:** a streaming chat endpoint on the backend (new work — scope with LLM layer). Until it exists, Phase 6.7 can ship against a mocked SSE responder during dev.

**Deliverables**
- [ ] `/chat` route: conversation list (sidebar), message thread, composer
- [ ] Streaming message rendering via `fetch` + `ReadableStream` (or the `ai` SDK's framework-agnostic helpers) with typing indicator
- [ ] Stock-context chip: if user navigated from `/stocks/:symbol`, chip is pre-populated; removable; adds/removes from the system prompt
- [ ] Zustand `chatStore`: active conversation, messages, pending symbols in context
- [ ] Structured response rendering: if backend returns a tool-use block (e.g. a score card), render it as a card, not plain text
- [ ] Stop-generation button, copy-message, retry
- [ ] Persist conversations in `localStorage` (v1); DB persistence deferred

**Exit criteria**
- Opening `/chat` from a stock page carries that symbol as context
- Streaming feels responsive (first token < 1s in local dev)

---

## Phase 6.8 — Settings, Polish, Build

**Goal:** configurable, accessible, fast, shippable.

**Deliverables**
- [ ] `/settings` route:
  - Scoring weight sliders (read/write `/api/v1/config`) — live preview of how weights re-rank top 10
  - Provider display (data/news/LLM) — read-only for now
  - Pipeline schedule (enable/disable, time-of-day)
  - Theme (light/dark/system), density (compact/comfy)
- [ ] Accessibility pass: keyboard nav, focus rings, aria labels, color contrast ≥ AA
- [ ] Performance: route-level code splitting via `React.lazy` + `Suspense`, lazy-load charts, memoize heavy cells, React Query staleness tuned per endpoint
- [ ] Error boundary per route with retry
- [ ] Component tests (Vitest + RTL) for hooks and critical components
- [ ] Playwright E2E: dashboard → stock detail → generate report (mocked LLM)
- [ ] Production build: `npm run build` emits static `dist/` — FastAPI can serve it with `StaticFiles` at `/`
- [ ] Update README and CLAUDE.md with final run commands

**Exit criteria**
- Lighthouse desktop: Performance ≥ 90, Accessibility ≥ 95
- `npm run build` produces a clean bundle; no console errors in `npm run preview`

---

## Dependency graph

```
6.1 Foundation ──┬──> 6.2 Browsing ──> 6.3 Detail ──┬──> 6.4 Intelligence
                 │                                  └──> 6.5 Recommendations
                 ├──> 6.6 Portfolio  (needs backend Phase 4B; UI scaffolds earlier)
                 ├──> 6.7 Chat       (needs backend streaming endpoint)
                 └──> 6.8 Polish     (runs continuously, locks in at the end)
```

Parallelization: 6.4 / 6.5 / 6.6 / 6.7 can proceed in any order once 6.3 is stable.

## Deferred / backlog

UI items scoped but not pinned to a phase yet live in [../TODO.md](../TODO.md): watchlist page, "add symbols" UI, auto-backfill toggle, breadcrumbs for stock navigation. Promote them into a phase when picked up.

---

## Commands (to be wired up during 6.1)

```bash
# First-time setup
cd ui
npm install
npx shadcn@latest init

# Dev
npm run dev          # Vite at http://localhost:5173

# Quality
npm run lint
npm run typecheck    # tsc --noEmit
npm run test         # Vitest
npm run test:e2e     # Playwright

# Build
npm run build        # vite build → dist/
npm run preview      # preview the production bundle
```
