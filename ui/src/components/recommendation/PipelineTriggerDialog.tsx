import { Loader2, Play, RefreshCw } from 'lucide-react';
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
import { useTriggerPipeline } from '@/features/recommendation/useTriggerPipeline';
import { usePipelineStore } from '@/store/pipeline';

interface PipelineTriggerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  symbolsCount: number;
  trigger?: React.ReactNode;
}

export function PipelineTriggerDialog({
  open,
  onOpenChange,
  symbolsCount,
  trigger,
}: PipelineTriggerDialogProps) {
  const mutation = useTriggerPipeline();
  const isRunning = usePipelineStore((s) => s.isRunning);
  const disabled = mutation.isPending || isRunning;

  async function handleRun() {
    try {
      await mutation.mutateAsync();
      onOpenChange(false);
    } catch {
      // error rendered below
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="size-4" />
            Run analysis pipeline
          </DialogTitle>
          <DialogDescription>
            Refreshes OHLCV and fundamentals for every tracked symbol, then re-ranks.
            Runs in the background; the UI refetches automatically when it's likely done.
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-muted/30 p-4 text-sm">
          <div className="flex items-baseline justify-between">
            <span className="text-muted-foreground">Symbols to refresh</span>
            <span className="font-semibold">{symbolsCount}</span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-muted-foreground">Estimated duration</span>
            <span className="font-medium">
              ~{Math.max(1, Math.round((symbolsCount * 2 + 30) / 60))} min
            </span>
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            {mutation.error instanceof Error
              ? mutation.error.message
              : 'Failed to trigger pipeline.'}
          </p>
        )}
        {isRunning && !mutation.isPending && (
          <p className="text-sm text-muted-foreground">
            A pipeline run is already in progress.
          </p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleRun} disabled={disabled}>
            {mutation.isPending ? <Loader2 className="animate-spin" /> : <Play />}
            {mutation.isPending ? 'Triggering…' : 'Run pipeline'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
