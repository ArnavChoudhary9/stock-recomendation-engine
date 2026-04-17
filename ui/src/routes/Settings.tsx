import { Settings as SettingsIcon } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';

export function Settings() {
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Scoring weights, providers, and theme." />
      <EmptyState
        icon={SettingsIcon}
        title="Phase 6.8 — coming up"
        description="Scoring weight sliders, provider display, pipeline schedule, density."
      />
    </div>
  );
}
