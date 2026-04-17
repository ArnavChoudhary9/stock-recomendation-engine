import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils/cn';

// Presets map to trailing-day windows; 'ALL' = repo max (10y cap server-side).
export type TimeframePreset = '1M' | '3M' | '6M' | '1Y' | '5Y' | 'ALL';

export interface TimeframeState {
  mode: 'preset' | 'custom';
  preset: TimeframePreset;
  startDate: string; // ISO YYYY-MM-DD
  endDate: string; // ISO YYYY-MM-DD
}

export const PRESET_DAYS: Record<TimeframePreset, number> = {
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
  '5Y': 365 * 5,
  ALL: 365 * 10,
};

export function defaultTimeframe(): TimeframeState {
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - PRESET_DAYS['1Y']);
  return {
    mode: 'preset',
    preset: '1Y',
    startDate: start.toISOString().slice(0, 10),
    endDate: today.toISOString().slice(0, 10),
  };
}

interface TimeframeSelectorProps {
  value: TimeframeState;
  onChange: (next: TimeframeState) => void;
  className?: string;
}

export function TimeframeSelector({ value, onChange, className }: TimeframeSelectorProps) {
  function selectPreset(preset: TimeframePreset) {
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - PRESET_DAYS[preset]);
    onChange({
      mode: 'preset',
      preset,
      startDate: start.toISOString().slice(0, 10),
      endDate: today.toISOString().slice(0, 10),
    });
  }

  function setCustomStart(date: string) {
    onChange({ ...value, mode: 'custom', startDate: date });
  }

  function setCustomEnd(date: string) {
    onChange({ ...value, mode: 'custom', endDate: date });
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <div role="radiogroup" aria-label="Timeframe preset" className="inline-flex gap-1">
        {(Object.keys(PRESET_DAYS) as TimeframePreset[]).map((p) => {
          const active = value.mode === 'preset' && value.preset === p;
          return (
            <button
              key={p}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => selectPreset(p)}
              className={cn(
                'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                active
                  ? 'border-primary/50 bg-primary/10 text-foreground'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground',
              )}
            >
              {p}
            </button>
          );
        })}
      </div>

      <span className="text-xs text-muted-foreground" aria-hidden>
        ·
      </span>

      <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span>From</span>
        <Input
          type="date"
          value={value.startDate}
          max={value.endDate}
          onChange={(e) => setCustomStart(e.target.value)}
          className="h-8 w-36 text-xs"
        />
      </label>
      <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span>to</span>
        <Input
          type="date"
          value={value.endDate}
          min={value.startDate}
          max={new Date().toISOString().slice(0, 10)}
          onChange={(e) => setCustomEnd(e.target.value)}
          className="h-8 w-36 text-xs"
        />
      </label>

      {value.mode === 'custom' && (
        <span className="text-[11px] text-muted-foreground">custom range</span>
      )}
    </div>
  );
}

// Returns the number of days between start and end (inclusive). Clamped to >= 1.
export function daysIn(range: TimeframeState): number {
  const start = new Date(range.startDate);
  const end = new Date(range.endDate);
  const diff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  return Math.max(1, diff);
}
