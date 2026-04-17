import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { NewsBundle } from '@/lib/types';

export function useStockNews(symbol: string | undefined) {
  return useQuery<NewsBundle>({
    queryKey: ['stock-news', symbol],
    queryFn: () => apiClient.get<NewsBundle>(endpoints.stockNews(symbol!)),
    enabled: Boolean(symbol),
    staleTime: 5 * 60_000,
  });
}

// POST isn't available; "refresh" is done by re-fetching with refresh=true.
export function useRefreshStockNews(symbol: string | undefined) {
  const qc = useQueryClient();
  return useMutation<NewsBundle, Error, void>({
    mutationFn: () =>
      apiClient.get<NewsBundle>(endpoints.stockNews(symbol!), {
        params: { refresh: true },
      }),
    onSuccess: (bundle) => {
      qc.setQueryData(['stock-news', symbol], bundle);
    },
  });
}
