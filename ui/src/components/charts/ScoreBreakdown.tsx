import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { InfoTip } from '@/components/shared/InfoTip';
import { INDICATORS } from '@/lib/indicators';
import { cn } from '@/lib/utils/cn';
import { scoreTone, titleCase } from '@/lib/utils/format';
import type { ScoringWeights, SubScores } from '@/lib/types';

const SUB_SCORE_INDICATOR: Partial<Record<keyof SubScores, string>> = {
  moving_average: 'sub_moving_average',
  momentum: 'sub_momentum',
  volume: 'sub_volume',
  volatility: 'sub_volatility',
  fundamental: 'sub_fundamental',
  support_resistance: 'sub_support_resistance',
  trend_following: 'sub_trend_following',
  mean_reversion: 'sub_mean_reversion',
};

interface ScoreBreakdownProps {
  score: number;
  subScores: SubScores;
  /** Optional — when present, each row shows its weight % and bars below
   *  are visually dimmed. Usually comes from the config snapshot. */
  weights?: Partial<ScoringWeights>;
  className?: string;
}

const ORDER: Array<keyof SubScores> = [
  'moving_average',
  'momentum',
  'volume',
  'volatility',
  'fundamental',
  'support_resistance',
  'trend_following',
  'mean_reversion',
];

const SHORT_LABEL: Partial<Record<keyof SubScores, string>> = {
  moving_average: 'MA',
  support_resistance: 'Support/Resist.',
  trend_following: 'Trend (MACD)',
  mean_reversion: 'Mean rev. (BB)',
};

const TONE_COLOR = {
  ok: 'hsl(142.1 70.6% 45.3%)',
  warn: 'hsl(37.7 92.1% 50.2%)',
  down: 'hsl(0 84.2% 60.2%)',
  neutral: 'hsl(215.4 16.3% 60%)',
};

export function ScoreBreakdown({ score, subScores, weights, className }: ScoreBreakdownProps) {
  // Sum configured weights so we can show each row's weight as a percentage.
  const weightTotal = weights
    ? ORDER.reduce((s, k) => s + (weights[k] ?? 0), 0)
    : 0;

  const rows = ORDER.map((key) => {
    const value = Number((subScores[key] * 100).toFixed(0));
    const w = weights?.[key];
    const weightPct =
      w !== undefined && weightTotal > 0 ? Math.round((w / weightTotal) * 100) : null;
    const label = SHORT_LABEL[key] ?? titleCase(key);
    return {
      key,
      label,
      value,
      tone: scoreTone(subScores[key]),
      weightPct,
      indicatorKey: SUB_SCORE_INDICATOR[key],
      // When a sub-score has 0 weight in the current config, dim it so the user
      // sees at a glance which components are actually moving the composite.
      inactive: weightPct === 0,
    };
  });

  return (
    <div
      className={cn(
        'grid gap-5 md:grid-cols-[auto_1fr] md:items-start',
        className,
      )}
    >
      <div className="flex items-center gap-4">
        <ScoreRing score={score} size={96} strokeWidth={8} />
        <div>
          <div className="flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
            Composite
            <InfoTip indicator="composite_score" iconSize={11} />
          </div>
          <div className="text-3xl font-semibold tracking-tight">
            {(score * 100).toFixed(0)}
          </div>
          <div className="text-xs text-muted-foreground">out of 100</div>
          {weights && weightTotal > 0 && (
            <div className="mt-1 text-[11px] text-muted-foreground">
              weights normalised from config
            </div>
          )}
        </div>
      </div>

      <div className="min-w-0">
        <ResponsiveContainer width="100%" height={Math.max(260, rows.length * 34)}>
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 48, bottom: 20, left: 4 }}
            barCategoryGap="25%"
          >
            <XAxis
              type="number"
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={130}
              interval={0}
              tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <ReferenceLine
              x={50}
              stroke="hsl(var(--border))"
              strokeDasharray="3 3"
            />
            <Tooltip
              cursor={{ fill: 'hsl(var(--muted) / 0.3)' }}
              content={<SubScoreTooltip />}
            />
            <Bar dataKey="value" radius={[4, 4, 4, 4]} barSize={16} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell
                  key={r.key}
                  fill={TONE_COLOR[r.tone]}
                  fillOpacity={r.inactive ? 0.25 : 1}
                />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                offset={8}
                fill="hsl(var(--foreground))"
                fontSize={11}
                formatter={(label: unknown) => String(label)}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {weights && weightTotal > 0 && (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Dimmed rows have 0 weight in config — they don't influence the composite score.
          </p>
        )}
      </div>
    </div>
  );
}

interface SubScoreTooltipPayload {
  label: string;
  value: number;
  weightPct: number | null;
  indicatorKey?: string;
}

function SubScoreTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: SubScoreTooltipPayload }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0]!.payload;
  const entry = row.indicatorKey ? INDICATORS[row.indicatorKey] : undefined;
  const weightHint = row.weightPct == null ? null : `weight ${row.weightPct}%`;
  return (
    <div className="max-w-xs rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <span className="font-semibold">{entry?.label ?? row.label}</span>
        <span className="font-mono tabular-nums">{row.value} / 100</span>
      </div>
      {weightHint && (
        <div className="text-[11px] text-muted-foreground">{weightHint}</div>
      )}
      {entry && <div className="mt-1.5 text-[11px] leading-relaxed">{entry.summary}</div>}
      {entry?.detail && (
        <div className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
          {entry.detail}
        </div>
      )}
    </div>
  );
}
