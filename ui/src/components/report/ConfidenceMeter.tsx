import { cn } from '@/lib/utils/cn';

interface ConfidenceMeterProps {
  value: number; // 0..1
  className?: string;
}

export function ConfidenceMeter({ value, className }: ConfidenceMeterProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone = value >= 0.7 ? 'ok' : value >= 0.4 ? 'warn' : 'down';
  const fill = {
    ok: 'bg-[hsl(var(--success))]',
    warn: 'bg-[hsl(var(--warning))]',
    down: 'bg-destructive',
  }[tone];

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="uppercase tracking-wide text-muted-foreground">LLM confidence</span>
        <span className="font-semibold">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full transition-all', fill)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
