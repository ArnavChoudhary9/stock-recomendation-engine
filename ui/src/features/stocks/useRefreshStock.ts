import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';

interface RefreshResult {
  symbol: string;
  bars_written: number;
}

export function useRefreshStock(symbol: string | undefined) {
  const qc = useQueryClient();
  return useMutation<RefreshResult, Error, void>({
    mutationFn: () => apiClient.post<RefreshResult>(endpoints.stockRefresh(symbol!)),
    onSuccess: () => {
      // Invalidate everything tied to this symbol so the page pulls fresh data.
      qc.invalidateQueries({ queryKey: ['stock', symbol] });
      qc.invalidateQueries({ queryKey: ['stock-ohlcv', symbol] });
      qc.invalidateQueries({ queryKey: ['stock-analysis', symbol] });
    },
  });
}
