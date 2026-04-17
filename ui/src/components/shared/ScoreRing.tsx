import { cn } from '@/lib/utils/cn';
import { formatScore, scoreTone } from '@/lib/utils/format';

interface ScoreRingProps {
  score: number | null | undefined;
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
}

export function ScoreRing({
  score,
  size = 56,
  strokeWidth = 5,
  className,
  label,
}: ScoreRingProps) {
  const tone = scoreTone(score);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = typeof score === 'number' && !Number.isNaN(score) ? Math.max(0, Math.min(1, score)) : 0;
  const offset = circumference * (1 - clamped);

  const stroke = {
    ok: 'hsl(var(--success))',
    warn: 'hsl(var(--warning))',
    down: 'hsl(var(--destructive))',
    neutral: 'hsl(var(--muted-foreground))',
  }[tone];

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      aria-label={label ?? `Score ${formatScore(score)}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          fill="none"
          style={{ transition: 'stroke-dashoffset 400ms ease' }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold">
        {formatScore(score)}
      </span>
    </div>
  );
}
