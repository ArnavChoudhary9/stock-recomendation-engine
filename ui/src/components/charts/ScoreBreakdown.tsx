import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { cn } from '@/lib/utils/cn';
import { scoreTone, titleCase } from '@/lib/utils/format';
import type { SubScores } from '@/lib/types';

interface ScoreBreakdownProps {
  score: number;
  subScores: SubScores;
  className?: string;
}

const ORDER: Array<keyof SubScores> = [
  'moving_average',
  'momentum',
  'volume',
  'volatility',
  'fundamental',
  'support_resistance',
];

const TONE_COLOR = {
  ok: 'hsl(142.1 70.6% 45.3%)', // --success
  warn: 'hsl(37.7 92.1% 50.2%)', // --warning
  down: 'hsl(0 84.2% 60.2%)', // --destructive
  neutral: 'hsl(215.4 16.3% 60%)',
};

export function ScoreBreakdown({ score, subScores, className }: ScoreBreakdownProps) {
  const rows = ORDER.map((key) => ({
    key,
    label: titleCase(key),
    value: Number((subScores[key] * 100).toFixed(0)),
    tone: scoreTone(subScores[key]),
  }));

  return (
    <div className={cn('flex flex-col gap-6 lg:flex-row lg:items-center', className)}>
      <div className="flex items-center gap-4">
        <ScoreRing score={score} size={96} strokeWidth={8} />
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Composite</div>
          <div className="text-2xl font-semibold tracking-tight">{(score * 100).toFixed(0)}</div>
          <div className="text-xs text-muted-foreground">out of 100</div>
        </div>
      </div>
      <div className="min-h-[160px] flex-1">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 24, bottom: 4, left: 4 }}
          >
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={120}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: 'hsl(var(--muted) / 0.3)' }}
              contentStyle={{
                background: 'hsl(var(--popover))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
              formatter={(v: number) => [`${v} / 100`, 'Score']}
            />
            <Bar dataKey="value" radius={[4, 4, 4, 4]} barSize={16}>
              {rows.map((r) => (
                <Cell key={r.key} fill={TONE_COLOR[r.tone]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
