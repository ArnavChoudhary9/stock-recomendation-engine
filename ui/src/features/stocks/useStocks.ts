import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { PaginatedResponse, StockInfo } from '@/lib/types';

interface UseStocksOptions {
  sector?: string;
  limit?: number;
  offset?: number;
}

export function useStocks({ sector, limit = 500, offset = 0 }: UseStocksOptions = {}) {
  return useQuery<PaginatedResponse<StockInfo>>({
    queryKey: ['stocks', { sector: sector ?? null, limit, offset }],
    queryFn: () =>
      apiClient.getPaginated<StockInfo>(endpoints.stocks, {
        params: { sector, limit, offset },
      }),
    staleTime: 60_000,
  });
}
