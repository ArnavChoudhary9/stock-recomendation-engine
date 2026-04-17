import { Link } from 'react-router-dom';
import { ExternalLink, Scale } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { ScoreRing } from '@/components/shared/ScoreRing';
import { SignalBadges } from '@/components/stock/SignalBadges';
import { formatPercent, titleCase } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';
import type { Recommendation, StockAnalysis, SubScores } from '@/lib/types';

interface CompareDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  analyses: StockAnalysis[];
}

const RECO_VARIANT: Record<Recommendation, 'success' | 'destructive' | 'secondary'> = {
  BUY: 'success',
  SELL: 'destructive',
  HOLD: 'secondary',
};

const SUB_SCORE_ROWS: Array<{ key: keyof SubScores; label: string }> = [
  { key: 'moving_average', label: 'Moving avg' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'volume', label: 'Volume' },
  { key: 'volatility', label: 'Volatility' },
  { key: 'fundamental', label: 'Fundamental' },
  { key: 'support_resistance', label: 'Support/Res' },
];

export function CompareDrawer({ open, onOpenChange, analyses }: CompareDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl lg:max-w-4xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Scale className="size-4" />
            Compare {analyses.length} stocks
          </SheetTitle>
          <SheetDescription>
            Score breakdown, key features, and signals side-by-side.
          </SheetDescription>
        </SheetHeader>

        {analyses.length === 0 ? (
          <div className="p-6 text-sm text-muted-foreground">
            Select 2–3 stocks in the table to compare.
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6">
            <div
              className="grid gap-6"
              style={{
                gridTemplateColumns: `repeat(${analyses.length}, minmax(0, 1fr))`,
              }}
            >
              {analyses.map((a) => (
                <div key={a.symbol} className="space-y-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <Link
                        to={`/stocks/${a.symbol}`}
                        className="inline-flex items-center gap-1 text-base font-semibold hover:underline"
                      >
                        {a.symbol}
                        <ExternalLink className="size-3" />
                      </Link>
                      <div className="mt-1">
                        <Badge variant={RECO_VARIANT[a.recommendation]}>
                          {a.recommendation}
                        </Badge>
                      </div>
                    </div>
                    <ScoreRing score={a.score} size={56} />
                  </div>

                  <section>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Sub-scores
                    </h3>
                    <div className="space-y-1.5">
                      {SUB_SCORE_ROWS.map((row) => (
                        <SubScoreBar
                          key={row.key}
                          label={row.label}
                          value={a.sub_scores[row.key]}
                        />
                      ))}
                    </div>
                  </section>

                  <section>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Key features
                    </h3>
                    <dl className="space-y-1 text-xs">
                      <FeatureRow label="RSI" value={a.features.momentum.rsi_14.toFixed(0)} />
                      <FeatureRow
                        label="5d return"
                        value={formatPercent(a.features.momentum.return_5d, true)}
                      />
                      <FeatureRow
                        label="20d return"
                        value={formatPercent(a.features.momentum.return_20d, true)}
                      />
                      <FeatureRow
                        label="MA alignment"
                        value={titleCase(a.moving_averages.alignment)}
                      />
                      <FeatureRow
                        label="Volume ratio"
                        value={`${a.features.volume.volume_ratio.toFixed(2)}×`}
                      />
                      <FeatureRow
                        label="ATR(14)"
                        value={a.features.volatility.atr_14.toFixed(2)}
                      />
                    </dl>
                  </section>

                  <section>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Signals
                    </h3>
                    <SignalBadges signals={a.signals} max={8} />
                  </section>

                  {a.recommendation_rationale && (
                    <section>
                      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Rationale
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        {a.recommendation_rationale}
                      </p>
                    </section>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function SubScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone =
    value >= 0.7
      ? 'bg-[hsl(var(--success))]'
      : value >= 0.4
        ? 'bg-[hsl(var(--warning))]'
        : 'bg-destructive';
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{(value * 100).toFixed(0)}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full transition-all', tone)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function FeatureRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
