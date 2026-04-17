import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Star } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PriceChart, PriceChartLegend } from '@/components/charts/PriceChart';
import { useOverlayState } from '@/components/charts/useOverlayState';
import { ScoreBreakdown } from '@/components/charts/ScoreBreakdown';
import { MACDChart } from '@/components/charts/MACDChart';
import {
  TimeframeSelector,
  defaultTimeframe,
} from '@/components/charts/TimeframeSelector';
import { MovingAveragesPanel } from '@/components/stock/MovingAveragesPanel';
import { IndicatorPanel } from '@/components/stock/IndicatorPanel';
import { FundamentalsTable } from '@/components/stock/FundamentalsTable';
import { SignalBadges } from '@/components/stock/SignalBadges';
import { NewsFeed } from '@/components/news/NewsFeed';
import { ReportCard } from '@/components/report/ReportCard';
import { useStock } from '@/features/stocks/useStock';
import { useStockAnalysis } from '@/features/stocks/useStockAnalysis';
import { useStockOhlcv } from '@/features/stocks/useStockOhlcv';
import { useRefreshStock } from '@/features/stocks/useRefreshStock';
import { useConfig } from '@/features/system/useConfig';
import {
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useWatchlist,
} from '@/features/watchlist/useWatchlist';
import { cn } from '@/lib/utils/cn';
import { formatCurrency } from '@/lib/utils/format';
import type { UTCTimestamp } from 'lightweight-charts';
import type { Recommendation, ScoringWeights } from '@/lib/types';

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

export function StockDetail() {
  const { symbol: raw } = useParams();
  const symbol = raw?.toUpperCase();

  const [timeframe, setTimeframe] = useState(defaultTimeframe());

  const detail = useStock(symbol);
  const analysis = useStockAnalysis(symbol);
  // Fetch the full history once (backend caps at 10y) so client-side overlays
  // (SMA 200, EMAs, Bollinger, MACD warm-up) always compute on every available
  // bar. The timeframe selector only zooms the visible axis via `visibleRange`.
  const ohlcv = useStockOhlcv(symbol, { days: 365 * 10 });
  const refresh = useRefreshStock(symbol);
  const config = useConfig();
  const watchlist = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const removeFromWatchlist = useRemoveFromWatchlist();
  const { overlays, toggle, toggleGroup } = useOverlayState();

  if (!symbol) return null;

  const isWatched = Boolean(watchlist.data?.some((w) => w.symbol === symbol));
  const watchPending =
    addToWatchlist.isPending || removeFromWatchlist.isPending;

  const info = detail.data?.info;
  const latestClose = detail.data?.latest_close ?? null;
  const a = analysis.data;
  const scoringWeights = extractScoringWeights(config.data?.processing);
  const visibleRange = toVisibleRange(timeframe.startDate, timeframe.endDate);

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/stocks">
          <ArrowLeft className="size-4" /> All stocks
        </Link>
      </Button>

      <PageHeader
        title={
          <HeaderTitle
            symbol={symbol}
            name={info?.name}
            recommendation={a?.recommendation}
          />
        }
        description={info?.sector ? `${info.sector} · ${info.exchange}` : undefined}
        actions={
          <>
            {latestClose !== null && (
              <div className="hidden text-right sm:block">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Last close
                </div>
                <div className="text-lg font-semibold">{formatCurrency(latestClose)}</div>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                isWatched
                  ? removeFromWatchlist.mutate(symbol)
                  : addToWatchlist.mutate({ symbol, notes: null })
              }
              disabled={watchPending}
              aria-pressed={isWatched}
            >
              <Star
                className={cn(
                  'size-4',
                  isWatched ? 'fill-[hsl(var(--warning))] text-[hsl(var(--warning))]' : '',
                )}
              />
              {isWatched ? 'Watching' : 'Watch'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refresh.mutate()}
              disabled={refresh.isPending}
            >
              <RefreshCw className={cn('size-4', refresh.isPending && 'animate-spin')} />
              {refresh.isPending ? 'Refreshing…' : 'Refresh data'}
            </Button>
          </>
        }
      />

      {refresh.isError && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          Refresh failed: {refresh.error?.message}
        </p>
      )}
      {refresh.isSuccess && refresh.data && (
        <p className="rounded-md border border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10 px-3 py-2 text-sm text-[hsl(var(--success))]">
          Refreshed {refresh.data.bars_written} bars for {refresh.data.symbol}.
        </p>
      )}

      {detail.isError && (
        <ErrorState
          title="Couldn't load stock"
          description={
            detail.error instanceof Error ? detail.error.message : undefined
          }
          onRetry={() => detail.refetch()}
        />
      )}

      {detail.isSuccess && a && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Score breakdown</CardTitle>
                <CardDescription>
                  Weighted composite across 8 sub-scores · edit weights in{' '}
                  <code className="rounded bg-muted px-1 py-0.5 text-[11px]">
                    config/processing.yaml
                  </code>
                </CardDescription>
              </div>
              <SignalBadges signals={a.signals} max={5} />
            </div>
          </CardHeader>
          <CardContent>
            <ScoreBreakdown
              score={a.score}
              subScores={a.sub_scores}
              weights={scoringWeights ?? undefined}
            />
            {a.recommendation_rationale && (
              <p className="mt-4 text-sm text-muted-foreground">{a.recommendation_rationale}</p>
            )}
          </CardContent>
        </Card>
      )}

      {!detail.isSuccess && detail.isLoading && <Skeleton className="h-40 w-full" />}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="news">News</TabsTrigger>
          <TabsTrigger value="report">Report</TabsTrigger>
          <TabsTrigger value="fundamentals">Fundamentals</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <Card>
            <CardHeader className="space-y-3">
              <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <CardTitle className="text-base">Price</CardTitle>
                  <CardDescription>
                    Daily candles · toggle any MA or BB overlay from the legend
                  </CardDescription>
                </div>
                <PriceChartLegend
                  overlays={overlays}
                  onToggle={toggle}
                  onToggleGroup={toggleGroup}
                />
              </div>
              <TimeframeSelector value={timeframe} onChange={setTimeframe} />
            </CardHeader>
            <CardContent className="space-y-4">
              {ohlcv.isLoading && <Skeleton className="h-[420px] w-full" />}
              {ohlcv.isError && (
                <ErrorState
                  title="Couldn't load chart data"
                  description={
                    ohlcv.error instanceof Error ? ohlcv.error.message : undefined
                  }
                  onRetry={() => ohlcv.refetch()}
                />
              )}
              {ohlcv.isSuccess && ohlcv.data.length === 0 && (
                <EmptyState
                  title="No OHLCV data yet"
                  description="Run backfill for this symbol, or widen the date range — no bars are stored in the selected window."
                />
              )}
              {ohlcv.isSuccess && ohlcv.data.length > 0 && (
                <>
                  <PriceChart
                    rows={ohlcv.data}
                    overlays={overlays}
                    visibleRange={visibleRange}
                    height={420}
                  />
                  <div className="border-t pt-3">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        MACD (12, 26, 9)
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        blue = line · amber = signal · bars = histogram
                      </span>
                    </div>
                    <MACDChart
                      rows={ohlcv.data}
                      visibleRange={visibleRange}
                      height={140}
                    />
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Indicators compute on all {ohlcv.data.length.toLocaleString()} bars — the
                    timeframe only zooms the view, so SMA 200 / EMA / Bollinger / MACD stay
                    accurate regardless of what's visible.
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            {a ? (
              <>
                <MovingAveragesPanel ma={a.moving_averages} />
                <IndicatorPanel
                  momentum={a.features.momentum}
                  volume={a.features.volume}
                  volatility={a.features.volatility}
                  supportResistance={a.features.support_resistance}
                  macd={a.features.macd}
                  bollinger={a.features.bollinger}
                />
              </>
            ) : analysis.isLoading ? (
              <>
                <Skeleton className="h-[280px] w-full" />
                <Skeleton className="h-[280px] w-full" />
              </>
            ) : (
              <EmptyState
                title="No analysis yet"
                description="Run the pipeline for this symbol to generate features, moving averages, and signals."
                className="lg:col-span-2"
              />
            )}
          </div>
        </TabsContent>

        <TabsContent value="news">
          <NewsFeed symbol={symbol} />
        </TabsContent>

        <TabsContent value="report">
          <ReportCard symbol={symbol} />
        </TabsContent>

        <TabsContent value="fundamentals">
          <FundamentalsTable fundamentals={detail.data?.fundamentals ?? null} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function HeaderTitle({
  symbol,
  name,
  recommendation,
}: {
  symbol: string;
  name?: string;
  recommendation?: Recommendation;
}) {
  return (
    <div className="flex items-center gap-3">
      <span>{symbol}</span>
      {recommendation && (
        <Badge variant={RECO_VARIANT[recommendation]}>{recommendation}</Badge>
      )}
      {name && (
        <span className="text-sm font-normal text-muted-foreground">· {name}</span>
      )}
    </div>
  );
}

// ISO date (YYYY-MM-DD) → UTC seconds, matching what lightweight-charts gets
// from the candle/overlay data so setVisibleRange lines up exactly with bars.
function toVisibleRange(
  startDate: string,
  endDate: string,
): { from: UTCTimestamp; to: UTCTimestamp } {
  const from = Math.floor(new Date(`${startDate}T00:00:00Z`).getTime() / 1000);
  const to = Math.floor(new Date(`${endDate}T00:00:00Z`).getTime() / 1000);
  return { from: from as UTCTimestamp, to: to as UTCTimestamp };
}

// Backend `/config` returns dicts (YAML dump). Pull scoring.weights defensively —
// missing or malformed keys fall back to undefined so ScoreBreakdown drops the
// weight-aware features instead of crashing.
function extractScoringWeights(
  processing: Record<string, unknown> | undefined,
): Partial<ScoringWeights> | null {
  if (!processing) return null;
  const scoring = processing.scoring as { weights?: Record<string, unknown> } | undefined;
  const raw = scoring?.weights;
  if (!raw || typeof raw !== 'object') return null;
  const out: Partial<ScoringWeights> = {};
  for (const key of [
    'moving_average',
    'momentum',
    'volume',
    'volatility',
    'fundamental',
    'support_resistance',
    'trend_following',
    'mean_reversion',
  ] as const) {
    const v = raw[key];
    if (typeof v === 'number') out[key] = v;
  }
  return out;
}
