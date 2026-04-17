import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowUp, ArrowUpDown, LineChart, Plus, Search, X } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useStocks } from '@/features/stocks/useStocks';
import { useDebounce } from '@/lib/hooks/useDebounce';
import { cn } from '@/lib/utils/cn';
import type { StockInfo } from '@/lib/types';

type SortKey = 'symbol' | 'name' | 'sector' | 'exchange';
type SortDir = 'asc' | 'desc';

export function Stocks() {
  const [searchParams, setSearchParams] = useSearchParams();
  const qInitial = searchParams.get('q') ?? '';
  const sectorParam = searchParams.get('sector') ?? '';
  const sortParam = (searchParams.get('sort') ?? 'symbol:asc') as `${SortKey}:${SortDir}`;
  const [sortKey, sortDir] = sortParam.split(':') as [SortKey, SortDir];

  const [q, setQ] = useState(qInitial);
  const debouncedQ = useDebounce(q, 200);

  const { data, isLoading, isError, error, refetch } = useStocks({ limit: 500 });
  const rows = useMemo(() => data?.data ?? [], [data]);

  const sectors = useMemo(() => {
    const set = new Set<string>();
    for (const s of rows) if (s.sector) set.add(s.sector);
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const needle = debouncedQ.trim().toLowerCase();
    return rows
      .filter((s) => !sectorParam || s.sector === sectorParam)
      .filter((s) => {
        if (!needle) return true;
        return (
          s.symbol.toLowerCase().includes(needle) || s.name.toLowerCase().includes(needle)
        );
      })
      .sort(compareBy(sortKey, sortDir));
  }, [rows, debouncedQ, sectorParam, sortKey, sortDir]);

  function updateParam(key: string, value: string | null) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  }

  function toggleSort(key: SortKey) {
    const nextDir: SortDir = sortKey === key && sortDir === 'asc' ? 'desc' : 'asc';
    updateParam('sort', `${key}:${nextDir}`);
  }

  // Sync the debounced search into the URL (not every keystroke).
  useEffect(() => {
    updateParam('q', debouncedQ || null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stocks"
        description={
          data
            ? `${filtered.length} of ${data.pagination.total} tracked stocks`
            : 'Browse and filter tracked NSE/BSE stocks.'
        }
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link to="/stocks/manage">
              <Plus className="size-4" /> Add / backfill
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search symbol or name…"
            className="pl-9"
          />
        </div>

        <SectorFilter
          value={sectorParam}
          options={sectors}
          onChange={(v) => updateParam('sector', v || null)}
        />

        {(debouncedQ || sectorParam) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setQ('');
              updateParam('q', null);
              updateParam('sector', null);
            }}
          >
            <X className="size-4" /> Clear
          </Button>
        )}
      </div>

      {isLoading && <TableSkeleton />}
      {isError && (
        <ErrorState
          title="Couldn't load stocks"
          description={error instanceof Error ? error.message : undefined}
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          icon={LineChart}
          title={rows.length === 0 ? 'No stocks tracked yet' : 'No matches'}
          description={
            rows.length === 0
              ? 'Run scripts/backfill.py to seed OHLCV + fundamentals data.'
              : 'Try adjusting your search or sector filter.'
          }
        />
      )}
      {!isLoading && !isError && filtered.length > 0 && (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHead
                  label="Symbol"
                  column="symbol"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="Name"
                  column="name"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="Sector"
                  column="sector"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="Exchange"
                  column="exchange"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <TableHead>Industry</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((s) => (
                <TableRow key={s.symbol}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/stocks/${s.symbol}`}
                      className="text-primary hover:underline"
                    >
                      {s.symbol}
                    </Link>
                  </TableCell>
                  <TableCell className="text-foreground">{s.name}</TableCell>
                  <TableCell className="text-muted-foreground">{s.sector ?? '—'}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{s.exchange}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{s.industry ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function compareBy(key: SortKey, dir: SortDir) {
  const mult = dir === 'asc' ? 1 : -1;
  return (a: StockInfo, b: StockInfo) => {
    const av = (a[key] ?? '') as string;
    const bv = (b[key] ?? '') as string;
    return av.localeCompare(bv) * mult;
  };
}

function SortableHead({
  label,
  column,
  active,
  dir,
  onClick,
}: {
  label: string;
  column: SortKey;
  active: SortKey;
  dir: SortDir;
  onClick: (k: SortKey) => void;
}) {
  const isActive = active === column;
  const Icon = !isActive ? ArrowUpDown : dir === 'asc' ? ArrowUp : ArrowDown;
  return (
    <TableHead>
      <button
        type="button"
        onClick={() => onClick(column)}
        className={cn(
          'inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide transition-colors hover:text-foreground',
          isActive ? 'text-foreground' : 'text-muted-foreground',
        )}
      >
        {label}
        <Icon className="size-3" />
      </button>
    </TableHead>
  );
}

function SectorFilter({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 rounded-md border border-input bg-background px-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label="Filter by sector"
    >
      <option value="">All sectors</option>
      {options.map((s) => (
        <option key={s} value={s}>
          {s}
        </option>
      ))}
    </select>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2 rounded-lg border bg-card p-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

