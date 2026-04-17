import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import type { PortfolioOverview } from '@/lib/types';

export function usePortfolioOverview() {
  return useQuery<PortfolioOverview, APIError>({
    queryKey: ['portfolio', 'overview'],
    queryFn: () => apiClient.get<PortfolioOverview>(endpoints.portfolioOverview),
    staleTime: 30_000,
    // 501 / 404 = Phase 4B pending; don't retry, let the UI render the coming-soon state.
    retry: (count, err) => (isNotImplemented(err) ? false : count < 1),
  });
}
