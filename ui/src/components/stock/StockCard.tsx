import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { SignalBadges } from '@/components/stock/SignalBadges';
import { cn } from '@/lib/utils/cn';
import type { Recommendation, StockAnalysis } from '@/lib/types';

interface StockCardProps {
  analysis: StockAnalysis;
  sectorOverride?: string | null;
  className?: string;
}

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

export function StockCard({ analysis, sectorOverride, className }: StockCardProps) {
  const sector = sectorOverride ?? analysis.features.fundamentals?.market_cap_tier ?? null;

  return (
    <Card className={cn('group relative overflow-hidden transition-colors hover:border-primary/40', className)}>
      <Link
        to={`/stocks/${analysis.symbol}`}
        className="absolute inset-0 z-0"
        aria-label={`Open ${analysis.symbol} detail`}
      />
      <CardHeader className="relative z-10 flex flex-row items-start justify-between gap-4 space-y-0">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-tight">{analysis.symbol}</span>
            <Badge variant={RECO_VARIANT[analysis.recommendation]}>{analysis.recommendation}</Badge>
          </div>
          {sector && <p className="truncate text-xs text-muted-foreground">{sector}</p>}
        </div>
        <ScoreRing score={analysis.score} size={52} />
      </CardHeader>
      <CardContent className="relative z-10 space-y-3">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <Stat label="RSI" value={analysis.features.momentum.rsi_14.toFixed(0)} />
          <Stat
            label="5d"
            value={`${(analysis.features.momentum.return_5d * 100).toFixed(1)}%`}
            tone={analysis.features.momentum.return_5d >= 0 ? 'up' : 'down'}
          />
          <Stat
            label="MA"
            value={titleShort(analysis.moving_averages.alignment)}
            tone={
              analysis.moving_averages.alignment === 'bullish'
                ? 'up'
                : analysis.moving_averages.alignment === 'bearish'
                  ? 'down'
                  : 'neutral'
            }
          />
        </div>
        <SignalBadges signals={analysis.signals} max={3} />
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'up' | 'down' | 'neutral';
}) {
  const toneClass =
    tone === 'up'
      ? 'text-[hsl(var(--success))]'
      : tone === 'down'
        ? 'text-destructive'
        : 'text-foreground';
  return (
    <div className="rounded-md border bg-muted/20 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={cn('mt-0.5 text-sm font-medium', toneClass)}>{value}</div>
    </div>
  );
}

function titleShort(alignment: string) {
  return alignment.charAt(0).toUpperCase() + alignment.slice(1);
}
