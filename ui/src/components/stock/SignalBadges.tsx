import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils/cn';
import { titleCase } from '@/lib/utils/format';

// Signals the user should see first. Everything else is "other".
const PROMINENT = new Set(['golden_cross', 'death_cross', 'ma_bullish_stack', 'ma_bearish_stack']);

// Visual variant per signal — bullish = success, bearish = destructive, neutral = secondary.
const TONE: Record<string, 'success' | 'destructive' | 'warning' | 'secondary'> = {
  golden_cross: 'success',
  death_cross: 'destructive',
  ma_bullish_stack: 'success',
  ma_bearish_stack: 'destructive',
  price_above_200sma: 'success',
  price_below_200sma: 'destructive',
  momentum_strong: 'success',
  overbought: 'warning',
  oversold: 'warning',
  volume_spike: 'secondary',
  near_52w_high: 'success',
  near_52w_low: 'destructive',
};

interface SignalBadgesProps {
  signals: Record<string, boolean | string> | null | undefined;
  max?: number;
  className?: string;
}

export function SignalBadges({ signals, max = 4, className }: SignalBadgesProps) {
  if (!signals) return null;

  const active = Object.entries(signals)
    .filter(([, v]) => v === true || (typeof v === 'string' && v.length > 0))
    .map(([k]) => k);

  if (active.length === 0) {
    return (
      <span className={cn('text-xs text-muted-foreground', className)}>No active signals</span>
    );
  }

  const sorted = active.sort((a, b) => {
    const ap = PROMINENT.has(a) ? 0 : 1;
    const bp = PROMINENT.has(b) ? 0 : 1;
    return ap - bp;
  });
  const shown = sorted.slice(0, max);
  const rest = sorted.length - shown.length;

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {shown.map((key) => (
        <Badge key={key} variant={TONE[key] ?? 'secondary'}>
          {titleCase(key)}
        </Badge>
      ))}
      {rest > 0 && <Badge variant="outline">+{rest}</Badge>}
    </div>
  );
}
