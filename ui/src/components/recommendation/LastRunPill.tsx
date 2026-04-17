import { Clock, Loader2 } from 'lucide-react';
import { usePipelineStore } from '@/store/pipeline';
import { cn } from '@/lib/utils/cn';

export function LastRunPill() {
  const { lastTriggeredAt, lastCompletedAt, symbolsCount, isRunning } = usePipelineStore();

  if (isRunning) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full bg-[hsl(var(--warning))]/15 px-2.5 py-1 text-xs font-medium text-[hsl(var(--warning))]',
        )}
        title={`Pipeline running (${symbolsCount ?? '?'} symbols)`}
      >
        <Loader2 className="size-3 animate-spin" />
        Pipeline running
      </span>
    );
  }

  const stamp = lastCompletedAt ?? lastTriggeredAt;
  if (!stamp) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
        <Clock className="size-3" />
        Never run
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground"
      title={new Date(stamp).toLocaleString()}
    >
      <Clock className="size-3" />
      {formatRelative(stamp)}
    </span>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return 'just now';
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}
