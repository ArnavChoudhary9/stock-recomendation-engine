import { useState } from 'react';
import { Download, Plus } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBackfillStocks } from '@/features/stocks/useBackfill';
import { cn } from '@/lib/utils/cn';
import type { BackfillResult } from '@/lib/types';

export function ManageStocks() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Manage stocks"
        description="Add new symbols beyond NIFTY 50 and pull deep historical data."
      />
      <AddSymbolCard />
      <HistoricalBackfillCard />
    </div>
  );
}

// ——— Add a single symbol ———

function AddSymbolCard() {
  const [symbol, setSymbol] = useState('');
  const [days, setDays] = useState('365');
  const backfill = useBackfillStocks();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    backfill.mutate({ symbols: [sym], days: Math.max(1, Number(days) || 365) });
    setSymbol('');
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Add symbol</CardTitle>
        <CardDescription>
          Fetch OHLCV + fundamentals for a new NSE/BSE symbol. If it's already tracked, this
          extends the history window.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex-[2] space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">Symbol</span>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="HDFCBANK"
              required
            />
          </label>
          <label className="flex-1 space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              History (days)
            </span>
            <Input
              type="number"
              min={1}
              max={3650}
              value={days}
              onChange={(e) => setDays(e.target.value)}
            />
          </label>
          <Button type="submit" disabled={backfill.isPending}>
            <Plus className="size-4" />
            {backfill.isPending ? 'Fetching…' : 'Add + fetch'}
          </Button>
        </form>

        <BackfillStatus mutation={backfill} />
      </CardContent>
    </Card>
  );
}

// ——— Historical backfill with target date ———

function HistoricalBackfillCard() {
  const [symbolsText, setSymbolsText] = useState('');
  const [startDate, setStartDate] = useState('');
  const backfill = useBackfillStocks();

  const parsedSymbols = symbolsText
    .split(/[\s,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);

  const isValid = parsedSymbols.length > 0 && parsedSymbols.length <= 20 && Boolean(startDate);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;
    backfill.mutate({ symbols: parsedSymbols, start_date: startDate });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Backfill from date</CardTitle>
        <CardDescription>
          Pull historical bars from a specific date up to today for up to 20 symbols at a time. Use{' '}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">scripts/backfill.py</code>{' '}
          for larger batches.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <form onSubmit={submit} className="space-y-3">
          <label className="block space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Symbols <span className="normal-case text-muted-foreground">(comma- or space-separated, max 20)</span>
            </span>
            <textarea
              value={symbolsText}
              onChange={(e) => setSymbolsText(e.target.value.toUpperCase())}
              placeholder="RELIANCE, TCS, INFY, HDFCBANK"
              rows={2}
              className="flex min-h-[60px] w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <span className="text-xs text-muted-foreground">
              {parsedSymbols.length} symbol{parsedSymbols.length === 1 ? '' : 's'}
              {parsedSymbols.length > 20 && (
                <span className="ml-2 text-destructive">· over the 20-symbol limit</span>
              )}
            </span>
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Start date
            </span>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={new Date().toISOString().slice(0, 10)}
              required
            />
          </label>

          <Button type="submit" disabled={!isValid || backfill.isPending}>
            <Download className="size-4" />
            {backfill.isPending ? 'Running backfill…' : 'Run backfill'}
          </Button>
        </form>

        <BackfillStatus mutation={backfill} />
      </CardContent>
    </Card>
  );
}

// ——— Shared result surface ———

function BackfillStatus({
  mutation,
}: {
  mutation: ReturnType<typeof useBackfillStocks>;
}) {
  if (mutation.isPending) {
    return (
      <p className="text-sm text-muted-foreground">
        Fetching — up to ~2s per symbol because of provider throttling.
      </p>
    );
  }
  if (mutation.isError && mutation.error) {
    return (
      <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
        {mutation.error.message}
      </p>
    );
  }
  const result: BackfillResult | undefined = mutation.data;
  if (!result) return null;
  const total = Object.keys(result.written).length;
  const ok = total - result.failed.length;
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-3 text-sm">
      <p className="font-medium">
        {result.total_bars.toLocaleString()} bars written across {ok}/{total} symbols.
      </p>
      <ul className="mt-2 grid grid-cols-2 gap-1 text-xs tabular-nums sm:grid-cols-3">
        {Object.entries(result.written).map(([sym, bars]) => (
          <li key={sym} className="flex items-center justify-between gap-2">
            <span className={cn('font-medium', bars === 0 && 'text-destructive')}>{sym}</span>
            <span className="text-muted-foreground">{bars}</span>
          </li>
        ))}
      </ul>
      {result.failed.length > 0 && (
        <p className="mt-2 text-xs text-destructive">
          Failed: {result.failed.join(', ')}
        </p>
      )}
    </div>
  );
}
