import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { OHLCVRow } from '@/lib/types';

interface UseStockOhlcvOptions {
  days?: number;
}

export function useStockOhlcv(symbol: string | undefined, { days = 365 }: UseStockOhlcvOptions = {}) {
  return useQuery<OHLCVRow[]>({
    queryKey: ['stock-ohlcv', symbol, days],
    queryFn: () =>
      apiClient.get<OHLCVRow[]>(endpoints.stockOhlcv(symbol!), {
        params: { days },
      }),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });
}
