import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import { usePipelineStore } from '@/store/pipeline';
import type { PipelineRunResult } from '@/lib/types';

// Backend `/pipeline/run` dispatches a BackgroundTask — no completion signal is
// returned. We estimate a wait based on symbol count (≈2s per symbol + 30s),
// then invalidate recommendation + stock queries. Capped at 5min.
function estimateDurationMs(symbolsCount: number): number {
  const seconds = Math.min(300, symbolsCount * 2 + 30);
  return seconds * 1000;
}

export function useTriggerPipeline() {
  const queryClient = useQueryClient();
  const markTriggered = usePipelineStore((s) => s.markTriggered);
  const markCompleted = usePipelineStore((s) => s.markCompleted);

  return useMutation<PipelineRunResult>({
    mutationFn: () => apiClient.post<PipelineRunResult>(endpoints.pipelineRun),
    onSuccess: (result) => {
      markTriggered(result.symbols_count);
      const delay = estimateDurationMs(result.symbols_count);
      window.setTimeout(() => {
        markCompleted();
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
        queryClient.invalidateQueries({ queryKey: ['stocks'] });
        queryClient.invalidateQueries({ queryKey: ['stock-analysis'] });
        queryClient.invalidateQueries({ queryKey: ['stock-ohlcv'] });
      }, delay);
    },
  });
}
