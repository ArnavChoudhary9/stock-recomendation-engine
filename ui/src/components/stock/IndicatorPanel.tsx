import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils/cn';
import { formatCompact } from '@/lib/utils/format';
import type { Momentum, SupportResistance, Volatility, VolumeFeatures } from '@/lib/types';

interface IndicatorPanelProps {
  momentum: Momentum;
  volume: VolumeFeatures;
  volatility: Volatility;
  supportResistance: SupportResistance;
  className?: string;
}

export function IndicatorPanel({
  momentum,
  volume,
  volatility,
  supportResistance,
  className,
}: IndicatorPanelProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Indicators</CardTitle>
        <CardDescription>Momentum, volume, and volatility snapshot</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <RsiGauge value={momentum.rsi_14} />

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="5d return" value={formatSignedPct(momentum.return_5d)} tone={toneForReturn(momentum.return_5d)} />
          <Stat label="10d return" value={formatSignedPct(momentum.return_10d)} tone={toneForReturn(momentum.return_10d)} />
          <Stat label="20d return" value={formatSignedPct(momentum.return_20d)} tone={toneForReturn(momentum.return_20d)} />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Volume" value={formatCompact(volume.current_volume)} />
          <Stat
            label="Volume ratio"
            value={`${volume.volume_ratio.toFixed(2)}×`}
            hint={`20d avg ${formatCompact(volume.avg_volume_20d)}`}
            tone={volume.volume_ratio >= 2 ? 'ok' : volume.volume_ratio < 0.5 ? 'warn' : 'neutral'}
          />
          <Stat label="OBV" value={formatCompact(volume.obv)} />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Stat label="ATR (14)" value={volatility.atr_14.toFixed(2)} />
          <Stat label="σ (20)" value={volatility.std_dev_20.toFixed(2)} />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Stat
            label="52w high"
            value={supportResistance.high_52w.toFixed(2)}
            hint={`${supportResistance.distance_to_52w_high_pct.toFixed(2)}% away`}
            tone={supportResistance.near_52w_high ? 'ok' : 'neutral'}
          />
          <Stat
            label="52w low"
            value={supportResistance.low_52w.toFixed(2)}
            hint={`${supportResistance.distance_to_52w_low_pct.toFixed(2)}% away`}
            tone={supportResistance.near_52w_low ? 'down' : 'neutral'}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function RsiGauge({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const tone =
    value >= 70 ? 'warn' : value >= 50 ? 'ok' : value <= 30 ? 'down' : 'neutral';
  const color = {
    ok: 'bg-[hsl(var(--success))]',
    warn: 'bg-[hsl(var(--warning))]',
    down: 'bg-destructive',
    neutral: 'bg-muted-foreground/60',
  }[tone];
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          RSI 14
        </span>
        <span className="text-sm font-semibold">{value.toFixed(1)}</span>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
        <span className="pointer-events-none absolute top-0 h-full w-px bg-border" style={{ left: '30%' }} />
        <span className="pointer-events-none absolute top-0 h-full w-px bg-border" style={{ left: '70%' }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>0</span>
        <span>30</span>
        <span>70</span>
        <span>100</span>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'ok' | 'warn' | 'down' | 'neutral';
}) {
  const toneClass = {
    ok: 'text-[hsl(var(--success))]',
    warn: 'text-[hsl(var(--warning))]',
    down: 'text-destructive',
    neutral: 'text-foreground',
  }[tone];
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={cn('mt-1 text-base font-semibold', toneClass)}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

function formatSignedPct(v: number): string {
  const p = v * 100;
  return `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`;
}

function toneForReturn(v: number): 'ok' | 'down' | 'neutral' {
  if (v > 0.01) return 'ok';
  if (v < -0.01) return 'down';
  return 'neutral';
}
