import { Monitor, Moon, Sun, FileCode2, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useConfig, type ConfigSnapshot } from '@/features/system/useConfig';
import { useTheme } from '@/providers/ThemeProvider';
import { cn } from '@/lib/utils/cn';
import { titleCase } from '@/lib/utils/format';

export function Settings() {
  const { data, isLoading, isError, error, refetch } = useConfig();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Active runtime configuration, scoring weights, and UI preferences."
      />

      <AppearanceCard />

      {isLoading && <Skeleton className="h-64 w-full" />}
      {isError && (
        <ErrorState
          title="Couldn't load configuration"
          description={error instanceof Error ? error.message : undefined}
          onRetry={() => refetch()}
        />
      )}
      {data && (
        <>
          <ScoringWeightsCard processing={data.processing} />
          <ProvidersCard snapshot={data} />
          <PipelineCard />
        </>
      )}
    </div>
  );
}

// ——— Appearance ———

function AppearanceCard() {
  const { theme, setTheme } = useTheme();
  const opts = [
    { value: 'light' as const, label: 'Light', icon: Sun },
    { value: 'dark' as const, label: 'Dark', icon: Moon },
    { value: 'system' as const, label: 'System', icon: Monitor },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Appearance</CardTitle>
        <CardDescription>Follow the OS, or force a mode.</CardDescription>
      </CardHeader>
      <CardContent>
        <div role="radiogroup" aria-label="Theme" className="inline-flex gap-2">
          {opts.map((o) => {
            const active = theme === o.value;
            return (
              <button
                key={o.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(o.value)}
                className={cn(
                  'inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  active
                    ? 'border-primary/50 bg-primary/10 text-foreground'
                    : 'border-border bg-background text-muted-foreground hover:text-foreground',
                )}
              >
                <o.icon className="size-4" />
                {o.label}
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ——— Scoring weights ———

interface ScoringBlock {
  weights?: Record<string, number>;
}

function ScoringWeightsCard({ processing }: { processing: Record<string, unknown> }) {
  const scoring = (processing.scoring ?? {}) as ScoringBlock;
  const weights = scoring.weights ?? {};
  const entries = Object.entries(weights).filter(
    ([, v]) => typeof v === 'number',
  ) as Array<[string, number]>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Scoring weights</CardTitle>
        <CardDescription>
          Composite score is a weighted sum of six sub-scores. Edit in{' '}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">
            config/processing.yaml
          </code>{' '}
          and restart the API to apply.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Scoring config not exposed by /config.</p>
        ) : (
          <ul className="space-y-3">
            {entries.map(([key, value]) => (
              <li key={key} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{titleCase(key)}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {(value * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-primary/70 transition-all"
                    style={{ width: `${Math.round(value * 100)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ——— Providers ———

function ProvidersCard({ snapshot }: { snapshot: ConfigSnapshot }) {
  const data = snapshot.data as { data?: { provider?: string; default_exchange?: string } };
  const news = snapshot.news as {
    news?: { provider?: string };
    sentiment?: { analyzer?: string };
  };
  const llm = (snapshot.llm ?? null) as {
    llm?: { model?: string; base_url?: string; fallback_models?: string[] };
  } | null;
  const api = snapshot.api as { api?: { host?: string; port?: number } };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Providers</CardTitle>
        <CardDescription>Current backing services — read-only view.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <ProviderRow
          label="Data provider"
          value={data.data?.provider ?? '—'}
          hint={data.data?.default_exchange}
        />
        <ProviderRow label="News provider" value={news.news?.provider ?? '—'} />
        <ProviderRow
          label="Sentiment analyzer"
          value={news.sentiment?.analyzer ?? '—'}
        />
        <ProviderRow
          label="LLM model"
          value={llm?.llm?.model ?? 'not configured'}
          hint={llm?.llm?.fallback_models?.length ? `+${llm.llm.fallback_models.length} fallbacks` : undefined}
        />
        <ProviderRow
          label="API"
          value={`${api.api?.host ?? '127.0.0.1'}:${api.api?.port ?? 8000}`}
          hint="dev proxy: /api → :8000"
        />
      </CardContent>
    </Card>
  );
}

function ProviderRow({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border bg-muted/20 px-3 py-2">
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="truncate text-sm font-medium">{value}</div>
        {hint && <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>}
      </div>
      <Badge variant="outline">
        <FileCode2 className="size-3" />
      </Badge>
    </div>
  );
}

// ——— Pipeline ———

function PipelineCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Pipeline</CardTitle>
        <CardDescription>
          Manual EOD refresh across all tracked symbols. Scheduled runs aren't wired up yet — see{' '}
          <Link to="/" className="text-primary hover:underline">
            TODO
          </Link>
          .
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link to="/recommendations">
            <Play className="size-4" /> Open pipeline controls
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
