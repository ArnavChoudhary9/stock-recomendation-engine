import { MessageSquare } from 'lucide-react';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';

export function Chat() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Chat"
        description="Conversational exploration with stock-context injection."
      />
      <EmptyState
        icon={MessageSquare}
        title="Phase 6.7 — coming up"
        description="Streaming chat UI wired to a new backend streaming endpoint."
      />
    </div>
  );
}
