import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { StockAnalysis } from '@/lib/types';

interface UseRecommendationsOptions {
  limit?: number;
  sector?: string;
}

export function useRecommendations({ limit = 10, sector }: UseRecommendationsOptions = {}) {
  return useQuery<StockAnalysis[]>({
    queryKey: ['recommendations', { limit, sector: sector ?? null }],
    queryFn: () =>
      apiClient.get<StockAnalysis[]>(endpoints.recommendations, {
        params: { limit, sector },
      }),
    staleTime: 30_000,
  });
}
