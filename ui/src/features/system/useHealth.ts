import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';
import type { HealthStatus } from '@/lib/types';

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => apiClient.get<HealthStatus>(endpoints.health),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });
}
