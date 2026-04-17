import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
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
import { cn } from '@/lib/utils/cn';
import { formatCurrency } from '@/lib/utils/format';
import type { Recommendation } from '@/lib/types';

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

export function StockDetail() {
  const { symbol: raw } = useParams();
  const symbol = raw?.toUpperCase();

  const detail = useStock(symbol);
  const analysis = useStockAnalysis(symbol);
  const ohlcv = useStockOhlcv(symbol, { days: 365 });
  const refresh = useRefreshStock(symbol);
  const { overlays, toggle } = useOverlayState();

  if (!symbol) return null;

  const info = detail.data?.info;
  const latestClose = detail.data?.latest_close ?? null;
  const a = analysis.data;

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
                <CardDescription>Weighted composite from 6 sub-scores</CardDescription>
              </div>
              <SignalBadges signals={a.signals} max={5} />
            </div>
          </CardHeader>
          <CardContent>
            <ScoreBreakdown score={a.score} subScores={a.sub_scores} />
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
            <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
              <div>
                <CardTitle className="text-base">Price</CardTitle>
                <CardDescription>
                  Daily candles · click any MA button to toggle its overlay
                </CardDescription>
              </div>
              <PriceChartLegend overlays={overlays} onToggle={toggle} />
            </CardHeader>
            <CardContent>
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
                  description="Run backfill for this symbol to populate the chart."
                />
              )}
              {ohlcv.isSuccess && ohlcv.data.length > 0 && (
                <PriceChart rows={ohlcv.data} overlays={overlays} height={420} />
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
