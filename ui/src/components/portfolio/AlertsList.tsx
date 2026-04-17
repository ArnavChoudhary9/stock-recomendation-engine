import { BellOff, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils/cn';
import { titleCase } from '@/lib/utils/format';
import type { Alert } from '@/lib/types';

interface AlertsListProps {
  alerts: Alert[];
  onDelete?: (id: string) => void;
  deletingId?: string;
}

export function AlertsList({ alerts, onDelete, deletingId }: AlertsListProps) {
  if (alerts.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
          <BellOff className="size-6 text-muted-foreground" />
          <p className="text-sm font-medium">No alerts</p>
          <p className="max-w-sm text-xs text-muted-foreground">
            Create a rule to get notified after the daily EOD pipeline when a condition is met.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((a) => (
        <div
          key={a.id}
          className={cn(
            'flex items-start justify-between gap-3 rounded-md border bg-card p-3 text-sm',
            a.acknowledged && 'opacity-60',
          )}
        >
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <Link
                to={`/stocks/${a.symbol}`}
                className="font-medium text-primary hover:underline"
              >
                {a.symbol}
              </Link>
              <Badge variant="outline">{titleCase(a.rule_id)}</Badge>
              {a.acknowledged && <Badge variant="secondary">Acknowledged</Badge>}
            </div>
            <p className="text-muted-foreground">{a.message}</p>
            <time className="text-xs text-muted-foreground">
              {new Date(a.timestamp).toLocaleString()}
            </time>
          </div>
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(a.id)}
              disabled={deletingId === a.id}
              aria-label={`Delete alert for ${a.symbol}`}
              title="Delete"
            >
              <Trash2 className="size-4" />
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
