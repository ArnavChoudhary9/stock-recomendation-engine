import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import type { StockReport } from '@/lib/types';

// GET caches 1h server-side. UI caches for 10 min to avoid refetching on every
// tab switch. Regeneration forces a fresh LLM call via POST.
export function useStockReport(symbol: string | undefined) {
  return useQuery<StockReport, APIError>({
    queryKey: ['stock-report', symbol],
    queryFn: () => apiClient.get<StockReport>(endpoints.stockReport(symbol!)),
    enabled: Boolean(symbol),
    staleTime: 10 * 60_000,
    retry: (failureCount, err) => {
      // 503 = LLM unconfigured; don't retry, let the UI render the empty state.
      if (err instanceof APIError && err.status === 503) return false;
      return failureCount < 1;
    },
  });
}

export function useRegenerateReport(symbol: string | undefined) {
  const qc = useQueryClient();
  return useMutation<StockReport, APIError, void>({
    mutationFn: () => apiClient.post<StockReport>(endpoints.stockReport(symbol!)),
    onSuccess: (report) => {
      qc.setQueryData(['stock-report', symbol], report);
    },
  });
}
