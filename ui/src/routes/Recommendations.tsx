import { ListOrdered } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';

export function Recommendations() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Recommendations"
        description="Ranked stocks with scores, signals, and sentiment."
      />
      <EmptyState
        icon={ListOrdered}
        title="Phase 6.5 — coming up"
        description="Full ranked table, compare mode, and pipeline trigger."
      />
    </div>
  );
}
