import { Briefcase } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';

export function Portfolio() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio"
        description="Holdings overlaid with the scoring engine's view."
      />
      <EmptyState
        icon={Briefcase}
        title="Connect Kite — coming soon"
        description="Portfolio integration (Phase 4B) is deferred on the backend. Phase 6.6 will light this up once the API endpoints return real data."
      />
    </div>
  );
}
