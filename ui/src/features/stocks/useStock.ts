import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { StockDetail } from '@/lib/types';

export function useStock(symbol: string | undefined) {
  return useQuery<StockDetail>({
    queryKey: ['stock', symbol],
    queryFn: () => apiClient.get<StockDetail>(endpoints.stock(symbol!)),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });
}
