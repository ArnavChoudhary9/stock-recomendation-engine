import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { StockAnalysis } from '@/lib/types';

export function useStockAnalysis(symbol: string | undefined) {
  return useQuery<StockAnalysis>({
    queryKey: ['stock-analysis', symbol],
    queryFn: () => apiClient.get<StockAnalysis>(endpoints.stockAnalysis(symbol!)),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });
}
