import { Briefcase, Clock, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { KiteConnectBanner } from '@/components/portfolio/KiteConnectBanner';
import { PortfolioKPIs } from '@/components/portfolio/PortfolioKPIs';
import { AllocationPie } from '@/components/portfolio/AllocationPie';
import { HoldingsTable } from '@/components/portfolio/HoldingsTable';
import { ConcentrationWarnings } from '@/components/portfolio/ConcentrationWarnings';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import { usePortfolioOverview } from '@/features/portfolio/usePortfolioOverview';

export function Portfolio() {
  const { data, isLoading, isError, error, refetch } = usePortfolioOverview();
  const pending = isError && isNotImplemented(error);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio"
        description={
          data
            ? `As of ${new Date(data.as_of).toLocaleString()}${data.stale ? ' · stale (from cache)' : ''}`
            : 'Holdings overlaid with the scoring engine view.'
        }
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link to="/portfolio/alerts">
              <AlertCircle className="size-4" /> Alerts
            </Link>
          </Button>
        }
      />

      <KiteConnectBanner />

      {pending && (
        <EmptyState
          icon={Clock}
          title="Portfolio view — coming soon"
          description="Backend endpoints for holdings, positions, and performance are pinned to Phase 4B. The layout you're seeing is wired up; once 4B lands, your real Kite data will populate here."
        />
      )}

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {isError && !pending && (
        <ErrorState
          title="Couldn't load portfolio"
          description={error instanceof Error ? error.message : undefined}
          onRetry={() => refetch()}
        />
      )}

      {data && (
        <>
          {data.stale && (
            <div className="flex items-center gap-2 rounded-md border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-3 py-2 text-sm">
              <Badge variant="warning">Stale</Badge>
              <span className="text-muted-foreground">
                Showing cached data — Kite session may be expired.
              </span>
            </div>
          )}

          <PortfolioKPIs overview={data} />

          <ConcentrationWarnings warnings={data.concentration_warnings} />

          <div className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
            <AllocationPie allocation={data.allocation_by_sector} />
            {Object.keys(data.allocation_by_market_cap).length > 0 && (
              <AllocationPie
                allocation={data.allocation_by_market_cap}
                title="Market-cap tier"
                description="Large · mid · small · micro"
              />
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Holdings</CardTitle>
              <CardDescription>
                {data.holdings.length} {data.holdings.length === 1 ? 'holding' : 'holdings'} ·
                click a symbol to open its detail view.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <HoldingsTable holdings={data.holdings} scoreOverlay={data.score_overlay} />
            </CardContent>
          </Card>

          {data.positions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Open positions</CardTitle>
                <CardDescription>Intraday and delivery positions from Kite</CardDescription>
              </CardHeader>
              <CardContent>
                <PositionsList positions={data.positions} />
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Fallback for the rare case nothing else rendered (e.g. first load, no data, no error). */}
      {!data && !isLoading && !isError && (
        <EmptyState
          icon={Briefcase}
          title="Nothing to show"
          description="Connect Kite and run the pipeline."
        />
      )}
    </div>
  );
}

function PositionsList({ positions }: { positions: import('@/lib/types').Position[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {positions.map((p) => (
        <li
          key={`${p.symbol}-${p.product}`}
          className="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2"
        >
          <div className="flex items-center gap-2">
            <Link to={`/stocks/${p.symbol}`} className="font-medium text-primary hover:underline">
              {p.symbol}
            </Link>
            <Badge variant="outline">{p.product}</Badge>
            <span className="text-muted-foreground">
              qty {p.quantity} @ {p.average_price.toFixed(2)}
            </span>
          </div>
          <span
            className={
              p.pnl > 0
                ? 'font-medium text-[hsl(var(--success))]'
                : p.pnl < 0
                  ? 'font-medium text-destructive'
                  : 'font-medium'
            }
          >
            {p.pnl.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}
