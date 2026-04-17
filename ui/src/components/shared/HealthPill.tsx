import { CircleDot } from 'lucide-react';
import { useHealth } from '@/features/system/useHealth';
import { cn } from '@/lib/utils/cn';

export function HealthPill() {
  const { data, isLoading, isError } = useHealth();

  let label = 'connecting…';
  let tone: 'neutral' | 'ok' | 'warn' | 'down' = 'neutral';

  if (isError) {
    label = 'API down';
    tone = 'down';
  } else if (!isLoading && data) {
    label = `API ${data.status}`;
    tone = data.status === 'ok' ? 'ok' : data.status === 'degraded' ? 'warn' : 'down';
  }

  const toneClasses = {
    neutral: 'bg-muted text-muted-foreground',
    ok: 'bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]',
    warn: 'bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))]',
    down: 'bg-destructive/15 text-destructive',
  }[tone];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        toneClasses,
      )}
      title={data ? `uptime ${Math.round(data.uptime_seconds)}s` : undefined}
    >
      <CircleDot className="size-3" />
      {label}
    </span>
  );
}
