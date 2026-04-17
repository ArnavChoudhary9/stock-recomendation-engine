# Later TODOs / Backlog

Deferred work — not blocking current phases. Items here are captured so they don't get lost; pick them up between phases or when a related area is being touched.

---

## Data / Symbols management

- [x] ~~**Tracked-symbol list in the DB.**~~ Confirmed existing: the `stocks` table is populated by `DataService.ensure_stock` on any refresh. The `nifty50.txt` file is only a bootstrap list.
- [x] ~~**"Add symbols" UI.**~~ Shipped 2026-04-17: `/stocks/manage` has an Add-symbol form that hits `POST /stocks/backfill` with a configurable history window.
- [ ] **Auto-backfill toggle in Settings.** New option in `config/data.yaml` + `/settings` UI slider: when enabled, a scheduled job (APScheduler) runs the incremental backfill daily at a configurable time. Respect market holidays.
- [ ] **"Update all stocks" manual button in Settings.** One-click button that triggers `/pipeline/run` (which already refreshes every tracked symbol). Show progress + last-run timestamp. Should be usable even when auto-backfill is off.
- [x] ~~**Manual historical backfill with target date.**~~ Shipped 2026-04-17: `POST /api/v1/stocks/backfill` (accepts `symbols[]`, `start_date`, `days`, `force`, capped at 20) + `/stocks/manage` Backfill-from-date form.

## Portfolio / Watchlist

- [x] ~~**Watchlist page.**~~ Shipped 2026-04-17: `/watchlist` with add/remove + inline backfill, ScoreRing + SignalBadges overlay from `GET /watchlist/analysis/ranked`, "Watch" toggle on stock detail, Sidebar + command-palette entries.

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
