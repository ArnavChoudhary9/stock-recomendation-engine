import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import type { BackfillRequest, BackfillResult } from '@/lib/types';

// Invalidates the broad set of stock-scoped queries so freshly-backfilled
// symbols appear in the Stocks list + Recommendations + any open detail views.
export function useBackfillStocks() {
  const qc = useQueryClient();
  return useMutation<BackfillResult, APIError, BackfillRequest>({
    mutationFn: (body) => apiClient.post<BackfillResult>(endpoints.stocksBackfill, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stocks'] });
      qc.invalidateQueries({ queryKey: ['recommendations'] });
      qc.invalidateQueries({ queryKey: ['stock-ohlcv'] });
      qc.invalidateQueries({ queryKey: ['stock-analysis'] });
    },
  });
}
