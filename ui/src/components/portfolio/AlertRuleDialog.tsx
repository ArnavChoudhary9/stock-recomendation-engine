import { useState } from 'react';
import { Plus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useCreateAlertRule, type NewAlertRule } from '@/features/portfolio/useAlerts';
import type { AlertType } from '@/lib/types';

const ALERT_OPTIONS: Array<{ value: AlertType; label: string; hint: string }> = [
  { value: 'score_drop', label: 'Score drops below', hint: 'e.g. 0.30' },
  { value: 'price', label: 'Price drops below', hint: 'e.g. 2450.00' },
  { value: 'volume_spike', label: 'Volume spike above', hint: 'e.g. 3.0× avg' },
  { value: 'sentiment', label: 'Sentiment drops below', hint: 'e.g. -0.50' },
  { value: 'signal_change', label: 'Signal change (any)', hint: '0 (ignored)' },
];

export function AlertRuleDialog() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<AlertType>('score_drop');
  const [symbol, setSymbol] = useState('');
  const [threshold, setThreshold] = useState('0.3');
  const createRule = useCreateAlertRule();

  const reset = () => {
    setType('score_drop');
    setSymbol('');
    setThreshold('0.3');
    createRule.reset();
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: NewAlertRule = {
      type,
      symbol: symbol.trim() ? symbol.trim().toUpperCase() : null,
      threshold: Number(threshold),
    };
    await createRule.mutateAsync(body);
    setOpen(false);
    reset();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" /> New rule
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Create alert rule</DialogTitle>
            <DialogDescription>
              Fires after the daily EOD pipeline run when the condition is met.
            </DialogDescription>
          </DialogHeader>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Trigger</span>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as AlertType)}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {ALERT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium">
              Symbol <span className="text-muted-foreground">(optional — blank = all holdings)</span>
            </span>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="RELIANCE"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Threshold</span>
            <Input
              type="number"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder={ALERT_OPTIONS.find((o) => o.value === type)?.hint ?? '0'}
            />
          </label>

          {createRule.error && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {createRule.error.message}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createRule.isPending}>
              {createRule.isPending ? 'Saving…' : 'Create rule'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
