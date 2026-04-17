import { ExternalLink } from 'lucide-react';
import { SentimentPill } from '@/components/news/SentimentPill';
import type { NewsReference, SentimentLabel } from '@/lib/types';

interface SourcesListProps {
  sources: NewsReference[];
}

export function SourcesList({ sources }: SourcesListProps) {
  if (sources.length === 0) return null;
  return (
    <div>
      <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Sources ({sources.length})
      </h4>
      <ul className="space-y-2">
        {sources.map((s) => (
          <li
            key={s.url}
            className="flex items-start justify-between gap-3 rounded-md border bg-muted/20 p-3 text-sm"
          >
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer noopener"
              className="min-w-0 flex-1 leading-snug hover:text-primary"
            >
              <span className="font-medium">{s.title}</span>
              <ExternalLink className="ml-1 inline size-3 opacity-60" />
              <div className="mt-0.5 text-xs text-muted-foreground">
                {s.source} · {new Date(s.published_at).toLocaleDateString()}
              </div>
            </a>
            <SentimentPill
              score={s.sentiment_score}
              label={s.sentiment_label as SentimentLabel}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
