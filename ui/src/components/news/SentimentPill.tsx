import { cn } from '@/lib/utils/cn';
import type { SentimentLabel } from '@/lib/types';

interface SentimentPillProps {
  score: number; // -1..+1
  label?: SentimentLabel;
  className?: string;
}

export function SentimentPill({ score, label, className }: SentimentPillProps) {
  const tone = toneFor(score);
  const toneClass = {
    positive: 'bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]',
    negative: 'bg-destructive/15 text-destructive',
    neutral: 'bg-muted text-muted-foreground',
  }[tone];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums',
        toneClass,
        className,
      )}
      title={label ? `${label} (${score.toFixed(2)})` : `${score.toFixed(2)}`}
    >
      <Arrow tone={tone} />
      {score >= 0 ? '+' : ''}
      {score.toFixed(2)}
    </span>
  );
}

function Arrow({ tone }: { tone: SentimentLabel }) {
  if (tone === 'positive') return <span aria-hidden>▲</span>;
  if (tone === 'negative') return <span aria-hidden>▼</span>;
  return <span aria-hidden>•</span>;
}

function toneFor(score: number): SentimentLabel {
  if (score >= 0.15) return 'positive';
  if (score <= -0.15) return 'negative';
  return 'neutral';
}
