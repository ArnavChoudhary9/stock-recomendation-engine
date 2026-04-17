import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  History,
  ListOrdered,
  Play,
  Scale,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
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
import { ScoreRing } from '@/components/shared/ScoreRing';
import { SignalBadges } from '@/components/stock/SignalBadges';
import { SectorMultiSelect } from '@/components/recommendation/SectorMultiSelect';
import { CompareDrawer } from '@/components/recommendation/CompareDrawer';
import { PipelineTriggerDialog } from '@/components/recommendation/PipelineTriggerDialog';
import { useRecommendations } from '@/features/recommendation/useRecommendations';
import { useStocks } from '@/features/stocks/useStocks';
import { cn } from '@/lib/utils/cn';
import { formatPercent } from '@/lib/utils/format';
import type { Recommendation, StockAnalysis } from '@/lib/types';

type SortKey = 'rank' | 'symbol' | 'score' | 'return_5d' | 'return_20d' | 'recommendation';
type SortDir = 'asc' | 'desc';

const MAX_COMPARE = 3;

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

export function Recommendations() {
  const recos = useRecommendations({ limit: 500 });
  const { data: stocksPage } = useStocks({ limit: 500 });
  const stocks = useMemo(() => stocksPage?.data ?? [], [stocksPage]);
  const stockSymbolsCount = stocksPage?.pagination.total ?? stocks.length;

  const symbolToSector = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const s of stocks) map.set(s.symbol, s.sector);
    return map;
  }, [stocks]);

  const allSectors = useMemo(() => {
    const set = new Set<string>();
    for (const s of stocks) if (s.sector) set.add(s.sector);
    return Array.from(set).sort();
  }, [stocks]);

  const [sectorFilter, setSectorFilter] = useState<string[]>([]);
  const [minScore, setMinScore] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [selected, setSelected] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [pipelineOpen, setPipelineOpen] = useState(false);

  const analyses = useMemo(() => recos.data ?? [], [recos.data]);

  // Backend returns descending-score order. "Rank" = original index.
  const ranked = useMemo(() => analyses.map((a, i) => ({ ...a, rank: i + 1 })), [analyses]);

  const filtered = useMemo(() => {
    return ranked.filter((a) => {
      if (a.score < minScore) return false;
      if (sectorFilter.length === 0) return true;
      const sector = symbolToSector.get(a.symbol);
      return sector != null && sectorFilter.includes(sector);
    });
  }, [ranked, minScore, sectorFilter, symbolToSector]);

  const sorted = useMemo(() => {
    const mult = sortDir === 'asc' ? 1 : -1;
    const arr = [...filtered];
    arr.sort((a, b) => {
      switch (sortKey) {
        case 'rank':
          return (a.rank - b.rank) * mult;
        case 'symbol':
          return a.symbol.localeCompare(b.symbol) * mult;
        case 'score':
          return (a.score - b.score) * mult;
        case 'return_5d':
          return (a.features.momentum.return_5d - b.features.momentum.return_5d) * mult;
        case 'return_20d':
          return (a.features.momentum.return_20d - b.features.momentum.return_20d) * mult;
        case 'recommendation':
          return a.recommendation.localeCompare(b.recommendation) * mult;
        default:
          return 0;
      }
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const selectedAnalyses = useMemo(
    () => ranked.filter((a) => selected.includes(a.symbol)),
    [ranked, selected],
  );

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'symbol' || key === 'rank' ? 'asc' : 'desc');
    }
  }

  function toggleSelect(symbol: string) {
    setSelected((prev) => {
      if (prev.includes(symbol)) return prev.filter((s) => s !== symbol);
      if (prev.length >= MAX_COMPARE) return prev;
      return [...prev, symbol];
    });
  }

  function clearFilters() {
    setSectorFilter([]);
    setMinScore(0);
  }

  const hasFilters = sectorFilter.length > 0 || minScore > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recommendations"
        description={
          analyses.length > 0
            ? `Ranked ${filtered.length} of ${analyses.length} tracked stocks by composite score.`
            : 'Ranked stocks with scores, signals, and sentiment.'
        }
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/recommendations/history">
                <History /> History
              </Link>
            </Button>
            <Button size="sm" onClick={() => setPipelineOpen(true)}>
              <Play /> Run pipeline
            </Button>
          </div>
        }
      />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <SectorMultiSelect
          options={allSectors}
          value={sectorFilter}
          onChange={setSectorFilter}
        />

        <ScoreRangeFilter value={minScore} onChange={setMinScore} />

        <div className="flex-1" />

        {selected.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCompareOpen(true)}
            disabled={selected.length < 2}
          >
            <Scale /> Compare ({selected.length}/{MAX_COMPARE})
          </Button>
        )}

        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X /> Clear
          </Button>
        )}
      </div>

      {recos.isLoading && <TableSkeleton />}
      {recos.isError && (
        <ErrorState
          title="Couldn't load recommendations"
          description={recos.error instanceof Error ? recos.error.message : undefined}
          onRetry={() => recos.refetch()}
        />
      )}
      {!recos.isLoading && !recos.isError && analyses.length === 0 && (
        <EmptyState
          icon={ListOrdered}
          title="No recommendations yet"
          description="Run the pipeline to seed ranked recommendations."
        />
      )}
      {!recos.isLoading && !recos.isError && analyses.length > 0 && sorted.length === 0 && (
        <EmptyState
          icon={ListOrdered}
          title="No matches"
          description="Try widening the score range or clearing sector filters."
        />
      )}
      {!recos.isLoading && !recos.isError && sorted.length > 0 && (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10" />
                <SortableHead
                  label="#"
                  column="rank"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                  className="w-14"
                />
                <SortableHead
                  label="Symbol"
                  column="symbol"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <TableHead>Sector</TableHead>
                <SortableHead
                  label="Score"
                  column="score"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="Reco"
                  column="recommendation"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="5d %"
                  column="return_5d"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <SortableHead
                  label="20d %"
                  column="return_20d"
                  active={sortKey}
                  dir={sortDir}
                  onClick={toggleSort}
                />
                <TableHead>Signals</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((a) => (
                <RecommendationRow
                  key={a.symbol}
                  analysis={a}
                  sector={symbolToSector.get(a.symbol) ?? null}
                  selected={selected.includes(a.symbol)}
                  onToggleSelect={() => toggleSelect(a.symbol)}
                  canSelect={selected.length < MAX_COMPARE}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CompareDrawer
        open={compareOpen}
        onOpenChange={setCompareOpen}
        analyses={selectedAnalyses}
      />

      <PipelineTriggerDialog
        open={pipelineOpen}
        onOpenChange={setPipelineOpen}
        symbolsCount={stockSymbolsCount}
      />
    </div>
  );
}

function RecommendationRow({
  analysis,
  sector,
  selected,
  onToggleSelect,
  canSelect,
}: {
  analysis: StockAnalysis & { rank: number };
  sector: string | null;
  selected: boolean;
  onToggleSelect: () => void;
  canSelect: boolean;
}) {
  const ret5 = analysis.features.momentum.return_5d;
  const ret20 = analysis.features.momentum.return_20d;
  return (
    <TableRow className={cn(selected && 'bg-accent/30')}>
      <TableCell className="w-10">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          disabled={!selected && !canSelect}
          aria-label={`Select ${analysis.symbol} for compare`}
          className="size-4 rounded border-input accent-primary"
        />
      </TableCell>
      <TableCell className="text-sm text-muted-foreground tabular-nums">
        {analysis.rank}
      </TableCell>
      <TableCell className="font-medium">
        <Link to={`/stocks/${analysis.symbol}`} className="text-primary hover:underline">
          {analysis.symbol}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground">{sector ?? '—'}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <ScoreRing score={analysis.score} size={36} strokeWidth={4} />
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={RECO_VARIANT[analysis.recommendation]}>
          {analysis.recommendation}
        </Badge>
      </TableCell>
      <TableCell className={cn('tabular-nums', toneClass(ret5))}>
        {formatPercent(ret5, true)}
      </TableCell>
      <TableCell className={cn('tabular-nums', toneClass(ret20))}>
        {formatPercent(ret20, true)}
      </TableCell>
      <TableCell>
        <SignalBadges signals={analysis.signals} max={3} />
      </TableCell>
    </TableRow>
  );
}

function toneClass(value: number): string {
  if (value > 0) return 'text-[hsl(var(--success))]';
  if (value < 0) return 'text-destructive';
  return 'text-muted-foreground';
}

function SortableHead({
  label,
  column,
  active,
  dir,
  onClick,
  className,
}: {
  label: string;
  column: SortKey;
  active: SortKey;
  dir: SortDir;
  onClick: (k: SortKey) => void;
  className?: string;
}) {
  const isActive = active === column;
  const Icon = !isActive ? ArrowUpDown : dir === 'asc' ? ArrowUp : ArrowDown;
  return (
    <TableHead className={className}>
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

function ScoreRangeFilter({
  value,
  onChange,
}: {
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="flex min-w-[220px] flex-col gap-1.5 rounded-md border bg-background px-3 py-2">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground">
          Min score
        </span>
        <span className="font-semibold tabular-nums">
          {Math.round(value * 100)}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={Math.round(value * 100)}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        aria-label="Minimum score filter"
      />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2 rounded-lg border bg-card p-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
