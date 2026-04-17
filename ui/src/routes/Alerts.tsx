import { Link } from 'react-router-dom';
import { ArrowLeft, Clock } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorState } from '@/components/shared/ErrorState';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { AlertRuleDialog } from '@/components/portfolio/AlertRuleDialog';
import { AlertsList } from '@/components/portfolio/AlertsList';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import { useAlerts, useDeleteAlertRule } from '@/features/portfolio/useAlerts';

export function Alerts() {
  const { data, isLoading, isError, error, refetch } = useAlerts();
  const deleteRule = useDeleteAlertRule();
  const pending = isError && isNotImplemented(error);

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/portfolio">
          <ArrowLeft className="size-4" /> Portfolio
        </Link>
      </Button>

      <PageHeader
        title="Alerts"
        description="Rules evaluated after the daily EOD pipeline run."
        actions={!pending ? <AlertRuleDialog /> : null}
      />

      {pending && (
        <EmptyState
          icon={Clock}
          title="Alerts — coming soon"
          description="Alert endpoints will be wired up with Phase 4B. The create/delete UI is ready."
        />
      )}

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {isError && !pending && (
        <ErrorState
          title="Couldn't load alerts"
          description={error instanceof Error ? error.message : undefined}
          onRetry={() => refetch()}
        />
      )}

      {data && (
        <AlertsList
          alerts={data}
          onDelete={(id) => deleteRule.mutate(id)}
          deletingId={deleteRule.variables}
        />
      )}
    </div>
  );
}
