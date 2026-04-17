# Later TODOs / Backlog

Deferred work — not blocking current phases. Items here are captured so they don't get lost; pick them up between phases or when a related area is being touched.

---

## Data / Symbols management

- [ ] **Move tracked-symbol list from file into the DB.** Today the watchlist to fetch is seeded from `config/symbols/nifty50.txt` via `scripts/backfill.py`. Promote it to a first-class `tracked_symbols` table (or reuse `stocks` with a boolean flag) so the user can add/remove symbols at runtime without editing files.
- [ ] **"Add symbols" UI.** Free-form input (or CSV paste) on `/settings` or a dedicated `/stocks/manage` route to add arbitrary NSE/BSE symbols beyond NIFTY 50. On add: validate against provider, backfill N days, persist to the tracked-symbols table.
- [ ] **Auto-backfill toggle in Settings.** New option in `config/data.yaml` + `/settings` UI slider: when enabled, a scheduled job (APScheduler) runs the incremental backfill daily at a configurable time. Respect market holidays.
- [ ] **"Update all stocks" manual button in Settings.** One-click button that triggers `/pipeline/run` (which already refreshes every tracked symbol). Show progress + last-run timestamp. Should be usable even when auto-backfill is off.
- [ ] **Manual historical backfill with target date.** UI form (Settings or `/stocks/manage`): pick a date, optionally a symbol subset, trigger a job that backfills OHLCV from that date up to today. Needs backend support — currently `scripts/backfill.py` is the only path; add an API endpoint that wraps the same `DataService.refresh_many` flow with a `start_date` parameter.

## Portfolio / Watchlist

- [ ] **Watchlist page.** New `/watchlist` route showing symbols the user is actively tracking (not the same as holdings). Requires wiring up the existing `watchlist_router` on the backend side into a feature hook + table UI. Good candidate for reusing `StockCard` + scoring overlay from Phase 6.2.

## UI — Navigation

- [ ] **Breadcrumbs for stock navigation.** Breadcrumb component in the shell showing `Stocks / <SYMBOL>` on the detail route, with a `‹ Prev / Next ›` control that walks through the currently-filtered stock list (so the user can flip through recommendations without bouncing back to the index).

## Engine / analytics

- [ ] **Add more metrics to the engine.** Candidates: MACD, Bollinger Bands, Stochastic, ADX, Chaikin Money Flow, put/call ratio (if available). Each new metric needs a sub-score contribution or a signal. Update `ScoringWeights` + `SubScores` contracts if added to the composite score.
- [ ] **Sector comparison of a stock.** On the stock detail page, show the stock's features relative to its sector — percentile ranks for PE, ROE, score, RSI, returns. Needs a backend endpoint like `/stocks/:symbol/sector-comparison` or expand `/stocks/:symbol/analysis` to include percentiles.

## UI — Content & Polish

- [ ] **Help / glossary page.** A `/help` route that explains every metric, signal, and sub-score in plain language — what "golden_cross" means, how the composite score is weighted, why RSI 70 means overbought. Link to it from IndicatorPanel / MovingAveragesPanel info-icons.
- [ ] **Bug: Recharts tooltip shows black text in dark mode.** In `components/charts/ScoreBreakdown.tsx` the tooltip background uses `--popover` but the inner row values inherit default black. Fix: add `itemStyle={{ color: 'hsl(var(--foreground))' }}` to the `<Tooltip>` element (and verify across all Recharts usages). Already applied in `AllocationPie` (Phase 6.6) — replicate.
- [ ] **Scoring-weights live preview.** Settings currently shows weights as read-only bars (editable in `config/processing.yaml`). Wire a write endpoint (`PUT /api/v1/config`) + client hook so sliders re-rank the top 10 on the fly.
- [ ] **Playwright E2E.** Smoke tests: dashboard renders, ⌘K jumps to a stock, stock detail loads chart with MA overlays, `/portfolio` shows the coming-soon state, theme toggle works. Requires `@playwright/test` + a dev-server fixture.
- [ ] **Serve `dist/` from FastAPI in production.** Mount `StaticFiles(directory="ui/dist", html=True)` at `/` in `src/api/app.py` behind an env flag so a single process serves API + UI for non-dev use.
- [ ] **Broader component test coverage.** Vitest covers the API client envelope logic today — extend to `ScoreBreakdown`, `useStocks`/`useRecommendations` hooks (wrapped in `QueryClientProvider`), and a render smoke test for each route.
- [ ] **Density toggle.** Compact/comfy mode in Settings to tighten row heights on Stocks and Recommendations tables.

---

## Ownership

- Data/scheduler items → backend (`src/data/*`, `src/scheduler/*`, `config/data.yaml`).
- UI items → `ui/src/routes/*`, `ui/src/features/*`.

Add new items above in the right section. When you pick one up, move it into the active phase plan ([ui/PHASES.md](ui/PHASES.md)) or open a commit against it directly.
