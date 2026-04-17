# UI — Stock Intelligence

Vite + React 18 + TypeScript strict SPA for the Stock Intelligence backend.

- Architecture spec: [CLEAN_UI_UX.md](CLEAN_UI_UX.md)
- Phase plan: [PHASES.md](PHASES.md)

## First-time setup

```bash
cd ui
npm install
```

No `npx shadcn init` needed — this repo already owns the primitives under `src/components/ui/`. To add more later:

```bash
npx shadcn@latest add dialog tabs table command
```

## Dev

```bash
npm run dev              # Vite at http://localhost:5173
```

The dev server proxies `/api/*` → `http://localhost:8000` (FastAPI). Start the backend separately:

```bash
uvicorn src.api.app:create_app --factory --reload
```

## Quality gates

```bash
npm run typecheck        # tsc --noEmit, strict mode
npm run lint
npm run test             # Vitest
```

## Production build

```bash
npm run build            # emits ./dist
npm run preview          # local preview
```

FastAPI can serve `ui/dist/` via `StaticFiles` in production (wire-up deferred to Phase 6.8).

## Structure

See [PHASES.md](PHASES.md) for the full layout. Quick tour:

- `src/routes/` — page components, one per URL
- `src/components/ui/` — shadcn primitives (owned, not installed)
- `src/components/layout/` — AppShell, Sidebar, TopBar
- `src/components/shared/` — PageHeader, EmptyState, ErrorState, StatCard, HealthPill, ThemeToggle
- `src/features/<domain>/` — React Query hooks per domain (e.g. `useHealth`)
- `src/lib/api/` — single fetch client, endpoint constants, error types
- `src/lib/types/` — TS mirrors of `src/contracts/*.py`
- `src/providers/` — QueryProvider, ThemeProvider

## Rules (from CLEAN_UI_UX.md)

1. No `fetch` in components. Go through `lib/api/client.ts` + a feature hook.
2. No hard-coded colors. Use Tailwind theme tokens (`bg-primary`, `text-muted-foreground`, …).
3. All primitives from `components/ui/`. Extend via composition.
4. Every async surface ships a skeleton. No bare spinners.
5. Strong types everywhere. If the backend changes a contract, update `lib/types/` in the same commit.
