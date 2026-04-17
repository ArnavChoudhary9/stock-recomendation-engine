# Later TODOs / Backlog

Deferred work — not blocking current phases. Items here are captured so they don't get lost; pick them up between phases or when a related area is being touched.

---

## Data / Symbols management

- [ ] **Move tracked-symbol list from file into the DB.** Today the watchlist to fetch is seeded from `config/symbols/nifty50.txt` via `scripts/backfill.py`. Promote it to a first-class `tracked_symbols` table (or reuse `stocks` with a boolean flag) so the user can add/remove symbols at runtime without editing files.
- [ ] **"Add symbols" UI.** Free-form input (or CSV paste) on `/settings` or a dedicated `/stocks/manage` route to add arbitrary NSE/BSE symbols beyond NIFTY 50. On add: validate against provider, backfill N days, persist to the tracked-symbols table.
- [ ] **Auto-backfill toggle in Settings.** New option in `config/data.yaml` + `/settings` UI slider: when enabled, a scheduled job (APScheduler) runs the incremental backfill daily at a configurable time. Respect market holidays.

## Portfolio / Watchlist

- [ ] **Watchlist page.** New `/watchlist` route showing symbols the user is actively tracking (not the same as holdings). Requires wiring up the existing `watchlist_router` on the backend side into a feature hook + table UI. Good candidate for reusing `StockCard` + scoring overlay from Phase 6.2.

## UI — Navigation

- [ ] **Breadcrumbs for stock navigation.** Breadcrumb component in the shell showing `Stocks / <SYMBOL>` on the detail route, with a `‹ Prev / Next ›` control that walks through the currently-filtered stock list (so the user can flip through recommendations without bouncing back to the index).

---

## Ownership

- Data/scheduler items → backend (`src/data/*`, `src/scheduler/*`, `config/data.yaml`).
- UI items → `ui/src/routes/*`, `ui/src/features/*`.

Add new items above in the right section. When you pick one up, move it into the active phase plan ([ui/PHASES.md](ui/PHASES.md)) or open a commit against it directly.
