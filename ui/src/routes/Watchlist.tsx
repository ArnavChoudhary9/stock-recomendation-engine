import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Plus, Star, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { SignalBadges } from '@/components/stock/SignalBadges';
import { useAddToWatchlist, useRemoveFromWatchlist, useWatchlist, useWatchlistRanked } from '@/features/watchlist/useWatchlist';
import { useBackfillStocks } from '@/features/stocks/useBackfill';
import { APIError } from '@/lib/api/errors';
import { cn } from '@/lib/utils/cn';
import type { WatchlistItem, StockAnalysis, Recommendation } from '@/lib/types';

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

export function Watchlist() {
  const list = useWatchlist();
  const ranked = useWatchlistRanked();
  const remove = useRemoveFromWatchlist();

  const items = list.data ?? [];
  const analysisBySymbol = new Map<string, StockAnalysis>();
  for (const a of ranked.data ?? []) analysisBySymbol.set(a.symbol, a);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Watchlist"
        description="Curated symbols. Independent from what's in the database — symbols here are bookmarked but OHLCV must still be fetched."
      />

      <AddForm />

      {list.isLoading && <Skeleton className="h-40 w-full" />}
      {list.isError && (
        <ErrorState
          title="Couldn't load watchlist"
          description={list.error instanceof Error ? list.error.message : undefined}
          onRetry={() => list.refetch()}
        />
      )}

      {!list.isLoading && !list.isError && items.length === 0 && (
        <EmptyState
          icon={Star}
          title="Your watchlist is empty"
          description="Add a symbol above, or bookmark one from a stock detail page."
        />
      )}

      {items.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <WatchlistCard
              key={item.symbol}
              item={item}
              analysis={analysisBySymbol.get(item.symbol)}
              onRemove={() => remove.mutate(item.symbol)}
              removing={remove.isPending && remove.variables === item.symbol}
            />
          ))}
        </div>
      )}

      {items.length > 0 && ranked.isLoading && (
        <p className="text-xs text-muted-foreground">Scoring watchlist…</p>
      )}
    </div>
  );
}

// ——— Add form (top of page) ———

function AddForm() {
  const [symbol, setSymbol] = useState('');
  const [notes, setNotes] = useState('');
  const [alsoFetch, setAlsoFetch] = useState(true);
  const add = useAddToWatchlist();
  const backfill = useBackfillStocks();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    try {
      await add.mutateAsync({ symbol: sym, notes: notes.trim() || null });
    } catch (err) {
      if (!(err instanceof APIError)) throw err;
      // Re-surface via mutation error state — the form already renders it.
      return;
    }
    if (alsoFetch) {
      backfill.mutate({ symbols: [sym] });
    }
    setSymbol('');
    setNotes('');
  }

  const addError = add.error?.message;
  const backfillResult = backfill.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Add symbol</CardTitle>
        <CardDescription>
          Bookmark any NSE/BSE symbol. "Also fetch data" triggers an initial backfill so the
          symbol shows a score immediately.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="flex flex-col gap-3 md:flex-row md:items-end">
          <label className="flex-1 space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">Symbol</span>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="RELIANCE"
              required
            />
          </label>
          <label className="flex-[2] space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Notes (optional)
            </span>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Why are you watching?"
            />
          </label>
          <label className="flex cursor-pointer select-none items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={alsoFetch}
              onChange={(e) => setAlsoFetch(e.target.checked)}
              className="size-4"
            />
            Also fetch data
          </label>
          <Button type="submit" disabled={add.isPending || backfill.isPending}>
            <Plus className="size-4" />
            {add.isPending || backfill.isPending ? 'Adding…' : 'Add'}
          </Button>
        </form>

        {addError && (
          <p className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {addError}
          </p>
        )}
        {backfill.isError && backfill.error && (
          <p className="mt-3 rounded-md border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-3 py-2 text-sm">
            Backfill failed: {backfill.error.message}. The symbol was bookmarked anyway — refresh
            later from the stock detail page.
          </p>
        )}
        {backfillResult && backfillResult.total_bars > 0 && (
          <p className="mt-3 rounded-md border border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10 px-3 py-2 text-sm text-[hsl(var(--success))]">
            Fetched {backfillResult.total_bars} bars across{' '}
            {Object.keys(backfillResult.written).length} symbol(s).
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ——— Card per watchlist item ———

function WatchlistCard({
  item,
  analysis,
  onRemove,
  removing,
}: {
  item: WatchlistItem;
  analysis: StockAnalysis | undefined;
  onRemove: () => void;
  removing: boolean;
}) {
  return (
    <Card className={cn('relative', removing && 'opacity-60')}>
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <Link to={`/stocks/${item.symbol}`} className="text-lg font-semibold tracking-tight text-primary hover:underline">
              {item.symbol}
            </Link>
            {analysis && (
              <Badge variant={RECO_VARIANT[analysis.recommendation]}>
                {analysis.recommendation}
              </Badge>
            )}
          </div>
          {item.notes && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{item.notes}</p>
          )}
          <time
            className="block text-[11px] text-muted-foreground"
            dateTime={item.added_at}
          >
            added {new Date(item.added_at).toLocaleDateString()}
          </time>
        </div>
        {analysis ? (
          <ScoreRing score={analysis.score} size={48} />
        ) : (
          <span className="text-xs text-muted-foreground" title="no analysis yet">
            <Eye className="size-4" />
          </span>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {analysis && <SignalBadges signals={analysis.signals} max={3} />}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/stocks/${item.symbol}`}>Open</Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            disabled={removing}
            aria-label={`Remove ${item.symbol} from watchlist`}
          >
            <Trash2 className="size-4" />
            Remove
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
