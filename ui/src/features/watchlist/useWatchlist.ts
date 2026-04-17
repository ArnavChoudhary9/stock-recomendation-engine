import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import type { AddToWatchlistRequest, StockAnalysis, WatchlistItem } from '@/lib/types';

const LIST_KEY = ['watchlist'] as const;
const RANKED_KEY = ['watchlist', 'ranked'] as const;

export function useWatchlist() {
  return useQuery<WatchlistItem[]>({
    queryKey: LIST_KEY,
    queryFn: () => apiClient.get<WatchlistItem[]>(endpoints.watchlist),
    staleTime: 60_000,
  });
}

export function useWatchlistRanked() {
  return useQuery<StockAnalysis[]>({
    queryKey: RANKED_KEY,
    queryFn: () => apiClient.get<StockAnalysis[]>(endpoints.watchlistRanked),
    staleTime: 30_000,
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation<WatchlistItem, APIError, AddToWatchlistRequest>({
    mutationFn: (body) => apiClient.post<WatchlistItem>(endpoints.watchlist, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: RANKED_KEY });
    },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation<void, APIError, string>({
    mutationFn: (symbol) => apiClient.delete<void>(endpoints.watchlistItem(symbol)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: RANKED_KEY });
    },
  });
}
