import { Newspaper, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { SentimentMeter } from './SentimentMeter';
import { NewsArticle } from './NewsArticle';
import { useStockNews, useRefreshStockNews } from '@/features/news/useStockNews';
import { cn } from '@/lib/utils/cn';

interface NewsFeedProps {
  symbol: string;
}

export function NewsFeed({ symbol }: NewsFeedProps) {
  const { data, isLoading, isError, error, refetch } = useStockNews(symbol);
  const refresh = useRefreshStockNews(symbol);

  if (isLoading) return <NewsFeedSkeleton />;
  if (isError) {
    return (
      <ErrorState
        title="Couldn't load news"
        description={error instanceof Error ? error.message : undefined}
        onRetry={() => refetch()}
      />
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <SentimentMeter
          score={data.aggregate_sentiment}
          articleCount={data.article_count}
          windowHours={data.time_window_hours}
          className="flex-1"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
        >
          <RefreshCw className={cn('size-4', refresh.isPending && 'animate-spin')} />
          {refresh.isPending ? 'Refreshing…' : 'Refresh'}
        </Button>
      </div>

      {data.articles.length === 0 ? (
        <EmptyState
          icon={Newspaper}
          title="No recent articles"
          description={`Nothing surfaced in the last ${data.time_window_hours}h.`}
        />
      ) : (
        <div className="space-y-3">
          {data.articles.map((a) => (
            <NewsArticle key={a.url} article={a} />
          ))}
        </div>
      )}
    </div>
  );
}

function NewsFeedSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24 w-full" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}
