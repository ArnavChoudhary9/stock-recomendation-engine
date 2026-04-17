import { Activity, Briefcase, LineChart, ListOrdered } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { StatCard } from '@/components/shared/StatCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StockCard } from '@/components/stock/StockCard';
import { useHealth } from '@/features/system/useHealth';
import { useRecommendations } from '@/features/recommendation/useRecommendations';
import { useStocks } from '@/features/stocks/useStocks';

export function Dashboard() {
  const { data: health } = useHealth();
  const recos = useRecommendations({ limit: 3 });
  const { data: stocksPage } = useStocks({ limit: 500 });
  const stockCount = stocksPage?.pagination.total ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Top recommendations, market overview, and pipeline status."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="API status"
          value={health?.status ?? '—'}
          hint={health ? `uptime ${Math.round(health.uptime_seconds)}s` : 'connecting…'}
          icon={Activity}
          trend={health?.status === 'ok' ? 'up' : 'neutral'}
        />
        <StatCard
          label="Stocks tracked"
          value={stockCount ?? '—'}
          hint={stockCount === 0 ? 'run backfill' : 'across NSE/BSE'}
          icon={LineChart}
        />
        <StatCard
          label="Top recommendations"
          value={recos.data?.length ?? '—'}
          hint="ranked by composite score"
          icon={ListOrdered}
        />
        <StatCard
          label="Portfolio value"
          value="—"
          hint="Phase 6.6 (Kite)"
          icon={Briefcase}
        />
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Top 3 recommendations</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/recommendations">View all</Link>
          </Button>
        </div>
        <TopRecommendations state={recos} />
      </section>
    </div>
  );
}

function TopRecommendations({
  state,
}: {
  state: ReturnType<typeof useRecommendations>;
}) {
  if (state.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div className="space-y-2">
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-3 w-28" />
              </div>
              <Skeleton className="size-13 rounded-full" />
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-5 w-3/4" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (state.isError) {
    return (
      <ErrorState
        title="Couldn't load recommendations"
        description={state.error instanceof Error ? state.error.message : 'Unknown error.'}
        onRetry={() => state.refetch()}
      />
    );
  }

  const items = state.data ?? [];
  if (items.length === 0) {
    return (
      <EmptyState
        icon={ListOrdered}
        title="No recommendations yet"
        description="Run backfill and the pipeline to seed data. scripts/backfill.py → scripts/run_pipeline.py"
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {items.map((a) => (
        <StockCard key={a.symbol} analysis={a} />
      ))}
    </div>
  );
}
