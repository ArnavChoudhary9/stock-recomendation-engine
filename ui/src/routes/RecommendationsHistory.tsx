import { useState } from 'react';
import { ArrowLeft, CalendarClock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Button } from '@/components/ui/button';

export function RecommendationsHistory() {
  const [date, setDate] = useState<string>(() => new Date().toISOString().slice(0, 10));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recommendation history"
        description="Historical snapshots of the ranked recommendations."
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link to="/recommendations">
              <ArrowLeft /> Back to recommendations
            </Link>
          </Button>
        }
      />

      <div className="flex flex-col gap-3 rounded-lg border bg-card p-4 sm:flex-row sm:items-center">
        <label htmlFor="history-date" className="text-sm font-medium">
          Snapshot date
        </label>
        <input
          id="history-date"
          type="date"
          value={date}
          max={new Date().toISOString().slice(0, 10)}
          onChange={(e) => setDate(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      <EmptyState
        icon={CalendarClock}
        title="Historical snapshots coming soon"
        description="The backend does not yet persist per-run snapshots. Once the pipeline writes them to the repository, this view will render the ranked table for any past date."
      />
    </div>
  );
}
