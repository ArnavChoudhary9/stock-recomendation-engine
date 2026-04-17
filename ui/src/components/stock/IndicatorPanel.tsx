import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { InfoTip } from '@/components/shared/InfoTip';
import { INDICATORS, type IndicatorEntry } from '@/lib/indicators';
import { cn } from '@/lib/utils/cn';
import { formatCompact } from '@/lib/utils/format';
import type {
  BollingerBands,
  MACDFeatures,
  Momentum,
  SupportResistance,
  Volatility,
  VolumeFeatures,
} from '@/lib/types';

interface IndicatorPanelProps {
  momentum: Momentum;
  volume: VolumeFeatures;
  volatility: Volatility;
  supportResistance: SupportResistance;
  macd?: MACDFeatures | null;
  bollinger?: BollingerBands | null;
  className?: string;
}

export function IndicatorPanel({
  momentum,
  volume,
  volatility,
  supportResistance,
  macd,
  bollinger,
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

        <div>
          <SectionLabel indicator="returns" />
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="5d return" value={formatSignedPct(momentum.return_5d)} tone={toneForReturn(momentum.return_5d)} />
            <Stat label="10d return" value={formatSignedPct(momentum.return_10d)} tone={toneForReturn(momentum.return_10d)} />
            <Stat label="20d return" value={formatSignedPct(momentum.return_20d)} tone={toneForReturn(momentum.return_20d)} />
          </div>
        </div>

        <div>
          <SectionLabel indicator="volume_ratio" label="Volume" />
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Volume" value={formatCompact(volume.current_volume)} />
            <Stat
              label="Volume ratio"
              value={`${volume.volume_ratio.toFixed(2)}×`}
              hint={`20d avg ${formatCompact(volume.avg_volume_20d)}`}
              tone={volume.volume_ratio >= 2 ? 'ok' : volume.volume_ratio < 0.5 ? 'warn' : 'neutral'}
              indicator="volume_ratio"
            />
            <Stat label="OBV" value={formatCompact(volume.obv)} indicator="obv" />
          </div>
        </div>

        <div>
          <SectionLabel label="Volatility" indicator="atr" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat label="ATR (14)" value={volatility.atr_14.toFixed(2)} indicator="atr" />
            <Stat label="σ (20)" value={volatility.std_dev_20.toFixed(2)} indicator="stddev" />
          </div>
        </div>

        <div>
          <SectionLabel label="52-week range" indicator="hl_52w" />
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
        </div>

        {macd && (
          <div className="space-y-2 rounded-md border bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                MACD
                <InfoTip indicator="macd" iconSize={12} />
              </span>
              {macd.crossover && (
                <Badge variant={macd.crossover === 'bullish' ? 'success' : 'destructive'}>
                  {macd.crossover === 'bullish' ? 'Bullish' : 'Bearish'}
                  {macd.crossover_days_ago !== null && (
                    <span className="ml-1 opacity-80">· {macd.crossover_days_ago}d</span>
                  )}
                </Badge>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Stat label="MACD line" value={macd.macd_line.toFixed(3)} />
              <Stat label="Signal" value={macd.signal_line.toFixed(3)} />
              <Stat
                label="Histogram"
                value={macd.histogram.toFixed(3)}
                tone={macd.histogram > 0 ? 'ok' : macd.histogram < 0 ? 'down' : 'neutral'}
              />
            </div>
          </div>
        )}

        {bollinger && (
          <div className="space-y-2 rounded-md border bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Bollinger Bands (20, 2σ)
                <InfoTip indicator="bollinger" iconSize={12} />
              </span>
              {bollinger.squeeze && <Badge variant="warning">Squeeze</Badge>}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Stat label="Upper" value={bollinger.upper.toFixed(2)} />
              <Stat label="Middle" value={bollinger.middle.toFixed(2)} />
              <Stat label="Lower" value={bollinger.lower.toFixed(2)} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Stat
                label="%B"
                value={bollinger.percent_b.toFixed(2)}
                hint={
                  bollinger.percent_b > 0.95
                    ? 'at/above upper band'
                    : bollinger.percent_b < 0.05
                      ? 'at/below lower band'
                      : 'inside bands'
                }
                tone={
                  bollinger.percent_b > 0.95
                    ? 'warn'
                    : bollinger.percent_b < 0.05
                      ? 'ok'
                      : 'neutral'
                }
              />
              <Stat
                label="Bandwidth"
                value={(bollinger.bandwidth * 100).toFixed(2) + '%'}
                hint={bollinger.squeeze ? 'volatility squeeze' : 'normal range'}
              />
            </div>
          </div>
        )}
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
        <span className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          RSI 14
          <InfoTip indicator="rsi" iconSize={12} />
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
  indicator,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'ok' | 'warn' | 'down' | 'neutral';
  indicator?: keyof typeof INDICATORS;
}) {
  const toneClass = {
    ok: 'text-[hsl(var(--success))]',
    warn: 'text-[hsl(var(--warning))]',
    down: 'text-destructive',
    neutral: 'text-foreground',
  }[tone];
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
        {label}
        {indicator && <InfoTip indicator={indicator} iconSize={11} />}
      </div>
      <div className={cn('mt-1 text-base font-semibold', toneClass)}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

function SectionLabel({
  label,
  indicator,
}: {
  label?: string;
  indicator: keyof typeof INDICATORS;
}) {
  const entry: IndicatorEntry | undefined = INDICATORS[indicator];
  const resolved = label ?? entry?.short ?? String(indicator);
  return (
    <div className="mb-2 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
      {resolved}
      <InfoTip indicator={indicator} iconSize={11} />
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
