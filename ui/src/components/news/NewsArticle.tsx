import { ExternalLink } from 'lucide-react';
import { SentimentPill } from './SentimentPill';
import { cn } from '@/lib/utils/cn';
import type { Article } from '@/lib/types';

interface NewsArticleProps {
  article: Article;
  className?: string;
}

export function NewsArticle({ article, className }: NewsArticleProps) {
  const published = new Date(article.published_at);
  const title = cleanTitle(article.title, article.source);
  const summary = cleanSummary(article.summary, title, article.source);
  return (
    <article
      className={cn(
        'group flex flex-col gap-2 rounded-md border bg-card p-4 transition-colors hover:border-primary/30',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer noopener"
          className="min-w-0 flex-1 text-sm font-medium leading-snug transition-colors group-hover:text-primary"
        >
          {title}
          <ExternalLink className="ml-1 inline size-3 opacity-60" />
        </a>
        <SentimentPill score={article.sentiment.score} label={article.sentiment.label} />
      </div>

      {summary && (
        <p className="line-clamp-3 text-sm text-muted-foreground">{summary}</p>
      )}

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground/80">{article.source}</span>
        <span aria-hidden>·</span>
        <time dateTime={article.published_at} title={published.toLocaleString()}>
          {formatRelative(published)}
        </time>
      </div>
    </article>
  );
}

function cleanTitle(title: string, source: string): string {
  const trimmed = title.trim();
  const sourceLc = source.trim().toLowerCase();
  if (!sourceLc) return trimmed;
  const match = trimmed.match(/^(.*?)[\s]*[-–—|:][\s]*([^\-–—|:]+)$/);
  if (match && match[1] && match[2] && match[2].trim().toLowerCase() === sourceLc) {
    return match[1].trim();
  }
  return trimmed;
}

function cleanSummary(
  summary: string | null | undefined,
  title: string,
  source: string,
): string {
  if (!summary) return '';
  const text = summary
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return '';
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9 ]+/g, '').replace(/\s+/g, ' ').trim();
  const nSummary = norm(text);
  const nTitle = norm(title);
  const nSource = norm(source);
  if (!nSummary || nSummary === nTitle || nSummary === nSource) return '';
  if (nTitle && nSummary.startsWith(nTitle)) {
    const tail = nSummary.slice(nTitle.length).trim();
    if (!tail || tail === nSource) return '';
  }
  if (nTitle) {
    const titleTokens = new Set(nTitle.split(' ').filter((t) => t.length > 2));
    if (titleTokens.size >= 4) {
      const summaryTokens = nSummary.split(' ').filter((t) => t.length > 2);
      const overlap = summaryTokens.filter((t) => titleTokens.has(t)).length;
      const ratio = overlap / titleTokens.size;
      if (ratio >= 0.85 && summaryTokens.length <= titleTokens.size + 3) return '';
    }
  }
  return text;
}

function formatRelative(d: Date): string {
  const diffMs = Date.now() - d.getTime();
  const hours = Math.floor(diffMs / (60 * 60 * 1000));
  if (hours < 1) {
    const min = Math.max(1, Math.floor(diffMs / 60_000));
    return `${min}m ago`;
  }
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 14) return `${days}d ago`;
  return d.toLocaleDateString();
}
