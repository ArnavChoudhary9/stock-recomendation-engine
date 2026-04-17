import { useEffect, useMemo, useState } from 'react';
import { BookOpen, Search } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  INDICATORS,
  INDICATOR_CATEGORIES,
  type IndicatorEntry,
} from '@/lib/indicators';
import { cn } from '@/lib/utils/cn';

const GLOSSARY: Array<{ term: string; definition: string }> = [
  {
    term: 'Alignment',
    definition:
      'Stack order of the three SMAs. Bullish = SMA20 > SMA50 > SMA200; bearish = reverse; mixed = anything else.',
  },
  {
    term: 'Composite score',
    definition:
      'Weighted blend of six deterministic sub-scores, normalised to 0–100. Weights live in config/processing.yaml.',
  },
  {
    term: 'Crossover',
    definition:
      'When a faster average crosses a slower one. SMA(50) above SMA(200) = golden cross; below = death cross.',
  },
  {
    term: 'Degraded report',
    definition:
      'LLM was unavailable or all fallback models failed — the UI shows the fact rather than an invented narrative.',
  },
  {
    term: 'Overbought / Oversold',
    definition:
      'RSI > 70 / RSI < 30. Useful in ranges; poor in strong trends, where RSI can stay extended for weeks.',
  },
  {
    term: 'Squeeze',
    definition:
      'Bollinger band width contracting below a threshold — volatility is unusually low and a move often follows.',
  },
  {
    term: 'Signal',
    definition:
      'Boolean flag derived from features (e.g. golden_cross, volume_spike, near_52w_high). Shown on cards and panels.',
  },
  {
    term: 'Sub-score',
    definition:
      'One of the 0–1 component scores (MA, momentum, volume, volatility, fundamental, support/resistance) that feed the composite.',
  },
];

export function Help() {
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (window.location.hash) {
      const id = window.location.hash.slice(1);
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        el.classList.add('ring-2', 'ring-primary/40');
        window.setTimeout(() => el.classList.remove('ring-2', 'ring-primary/40'), 1800);
      }
    }
  }, []);

  const needle = query.trim().toLowerCase();
  const entriesByCategory = useMemo(() => {
    const all = Object.values(INDICATORS);
    const matches = (e: IndicatorEntry): boolean => {
      if (!needle) return true;
      return (
        e.label.toLowerCase().includes(needle) ||
        e.short.toLowerCase().includes(needle) ||
        e.summary.toLowerCase().includes(needle) ||
        e.detail.toLowerCase().includes(needle) ||
        (e.interpretation ?? '').toLowerCase().includes(needle)
      );
    };
    const grouped: Record<IndicatorEntry['category'], IndicatorEntry[]> = {
      moving_average: [],
      momentum: [],
      volume: [],
      volatility: [],
      support_resistance: [],
      composite: [],
    };
    for (const entry of all.filter(matches)) grouped[entry.category].push(entry);
    return grouped;
  }, [needle]);

  const totalMatches = Object.values(entriesByCategory).reduce((n, e) => n + e.length, 0);

  const filteredGlossary = useMemo(
    () =>
      GLOSSARY.filter((g) =>
        !needle
          ? true
          : g.term.toLowerCase().includes(needle) ||
            g.definition.toLowerCase().includes(needle),
      ),
    [needle],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Help & indicator reference"
        description="What each indicator measures, how to read it, and how it feeds the score."
      />

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search indicators, terms, or descriptions…"
          className="pl-9"
        />
      </div>

      {totalMatches === 0 && filteredGlossary.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Nothing matched "{query}". Try a shorter term.
          </CardContent>
        </Card>
      ) : (
        <>
          {INDICATOR_CATEGORIES.map((cat) => {
            const entries = entriesByCategory[cat.key];
            if (entries.length === 0) return null;
            return (
              <section key={cat.key} className="space-y-3">
                <div className="flex items-baseline justify-between gap-4">
                  <h2 className="text-lg font-semibold tracking-tight">{cat.label}</h2>
                  <p className="text-xs text-muted-foreground">{cat.description}</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {entries.map((entry) => (
                    <IndicatorCard key={entry.key} entry={entry} />
                  ))}
                </div>
              </section>
            );
          })}

          {filteredGlossary.length > 0 && (
            <section className="space-y-3">
              <div className="flex items-baseline justify-between gap-4">
                <h2 className="text-lg font-semibold tracking-tight">Glossary</h2>
                <p className="text-xs text-muted-foreground">Quick definitions of common terms.</p>
              </div>
              <Card>
                <CardContent className="p-0">
                  <dl className="divide-y">
                    {filteredGlossary.map((g) => (
                      <div
                        key={g.term}
                        className="grid gap-1 px-4 py-3 sm:grid-cols-[160px_1fr] sm:gap-4"
                      >
                        <dt className="text-sm font-semibold">{g.term}</dt>
                        <dd className="text-sm text-muted-foreground">{g.definition}</dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>
            </section>
          )}
        </>
      )}

      <Card className="bg-muted/20">
        <CardContent className="flex items-start gap-3 py-4 text-sm text-muted-foreground">
          <BookOpen className="mt-0.5 size-4 shrink-0" />
          <p>
            This page is the reference for the indicators used by the platform. Inline question-mark
            icons throughout the app link back here — hover any indicator to see a short summary, or
            click through for the long form.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function IndicatorCard({ entry }: { entry: IndicatorEntry }) {
  return (
    <Card id={entry.key} className={cn('scroll-mt-20 transition-shadow')}>
      <CardHeader>
        <CardTitle className="text-base">{entry.label}</CardTitle>
        <CardDescription>{entry.summary}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{entry.detail}</p>
        {entry.interpretation && (
          <p className="rounded-md border-l-2 border-primary/40 bg-muted/20 px-3 py-2 text-muted-foreground">
            <span className="font-medium text-foreground">How to read it:</span>{' '}
            {entry.interpretation}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
