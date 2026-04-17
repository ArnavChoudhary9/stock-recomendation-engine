import { ArrowDown, ArrowRight, ArrowUp, TrendingDown, TrendingUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { InfoTip } from '@/components/shared/InfoTip';
import { cn } from '@/lib/utils/cn';
import type { MovingAverages, Slope } from '@/lib/types';

interface MovingAveragesPanelProps {
  ma: MovingAverages;
  className?: string;
}

const ALIGNMENT_VARIANT = {
  bullish: 'success',
  bearish: 'destructive',
  mixed: 'secondary',
} as const;

export function MovingAveragesPanel({ ma, className }: MovingAveragesPanelProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-1.5 text-base">
            Moving averages
            <InfoTip indicator="sma" />
          </CardTitle>
          <CardDescription>Alignment, crossover, and distance from price</CardDescription>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant={ALIGNMENT_VARIANT[ma.alignment]}>
            {ma.alignment === 'bullish' && <TrendingUp className="size-3" />}
            {ma.alignment === 'bearish' && <TrendingDown className="size-3" />}
            <span className="ml-1 capitalize">{ma.alignment}</span>
          </Badge>
          <InfoTip indicator="ma_alignment" iconSize={12} />
          {ma.crossover && (
            <>
              <Badge variant={ma.crossover === 'golden_cross' ? 'success' : 'destructive'}>
                {ma.crossover === 'golden_cross' ? 'Golden cross' : 'Death cross'}
                {ma.crossover_days_ago !== null && (
                  <span className="ml-1 opacity-80">· {ma.crossover_days_ago}d</span>
                )}
              </Badge>
              <InfoTip
                indicator={ma.crossover === 'golden_cross' ? 'golden_cross' : 'death_cross'}
                iconSize={12}
              />
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <MARow label="SMA 20" value={ma.sma_20} distancePct={ma.price_to_sma20_pct} />
          <MARow
            label="SMA 50"
            value={ma.sma_50}
            distancePct={ma.price_to_sma50_pct}
            slope={ma.sma50_slope}
          />
          <MARow
            label="SMA 200"
            value={ma.sma_200}
            distancePct={ma.price_to_sma200_pct}
            slope={ma.sma200_slope}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <MARow label="EMA 12" value={ma.ema_12} />
          <MARow label="EMA 26" value={ma.ema_26} />
        </div>
      </CardContent>
    </Card>
  );
}

function MARow({
  label,
  value,
  distancePct,
  slope,
}: {
  label: string;
  value: number;
  distancePct?: number;
  slope?: Slope;
}) {
  const distTone =
    distancePct === undefined
      ? ''
      : distancePct > 0
        ? 'text-[hsl(var(--success))]'
        : distancePct < 0
          ? 'text-destructive'
          : 'text-muted-foreground';

  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
        {slope && <SlopeIcon slope={slope} />}
      </div>
      <div className="mt-1 text-lg font-semibold">{value.toFixed(2)}</div>
      {distancePct !== undefined && (
        <div className={cn('mt-0.5 text-xs font-medium', distTone)}>
          {distancePct >= 0 ? '+' : ''}
          {distancePct.toFixed(2)}% from price
        </div>
      )}
    </div>
  );
}

function SlopeIcon({ slope }: { slope: Slope }) {
  const tone =
    slope === 'rising'
      ? 'text-[hsl(var(--success))]'
      : slope === 'falling'
        ? 'text-destructive'
        : 'text-muted-foreground';
  const Icon = slope === 'rising' ? ArrowUp : slope === 'falling' ? ArrowDown : ArrowRight;
  return <Icon className={cn('size-3', tone)} aria-label={`slope ${slope}`} />;
}
