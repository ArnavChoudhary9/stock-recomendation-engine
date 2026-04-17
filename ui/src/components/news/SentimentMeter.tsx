import { cn } from '@/lib/utils/cn';

interface SentimentMeterProps {
  score: number; // -1..+1
  articleCount: number;
  windowHours: number;
  className?: string;
}

export function SentimentMeter({ score, articleCount, windowHours, className }: SentimentMeterProps) {
  const pct = ((score + 1) / 2) * 100; // map -1..+1 to 0..100
  const tone = score >= 0.15 ? 'positive' : score <= -0.15 ? 'negative' : 'neutral';
  const toneLabel = tone === 'positive' ? 'Bullish' : tone === 'negative' ? 'Bearish' : 'Neutral';
  const toneFill = {
    positive: 'bg-[hsl(var(--success))]',
    negative: 'bg-destructive',
    neutral: 'bg-muted-foreground/60',
  }[tone];

  return (
    <div className={cn('rounded-lg border bg-muted/20 p-4', className)}>
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Aggregate sentiment
          </div>
          <div className="mt-0.5 text-lg font-semibold">
            {toneLabel}{' '}
            <span className="text-base font-normal text-muted-foreground">
              ({score >= 0 ? '+' : ''}
              {score.toFixed(2)})
            </span>
          </div>
        </div>
        <div className="text-right text-xs text-muted-foreground">
          <div>
            {articleCount} {articleCount === 1 ? 'article' : 'articles'}
          </div>
          <div>last {windowHours}h</div>
        </div>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full transition-all', toneFill)} style={{ width: `${pct}%` }} />
        <span
          className="pointer-events-none absolute top-0 h-full w-px bg-border"
          style={{ left: '50%' }}
          aria-hidden
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
    </div>
  );
}
