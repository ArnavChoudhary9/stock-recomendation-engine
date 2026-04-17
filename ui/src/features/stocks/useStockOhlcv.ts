import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { OHLCVRow } from '@/lib/types';

interface UseStockOhlcvOptions {
  days?: number;
  start?: string; // ISO YYYY-MM-DD — takes precedence over `days` when present
  end?: string;
}

export function useStockOhlcv(
  symbol: string | undefined,
  { days = 365, start, end }: UseStockOhlcvOptions = {},
) {
  return useQuery<OHLCVRow[]>({
    queryKey: ['stock-ohlcv', symbol, { days, start: start ?? null, end: end ?? null }],
    queryFn: () =>
      apiClient.get<OHLCVRow[]>(endpoints.stockOhlcv(symbol!), {
        params: { days, start, end },
      }),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });
}
