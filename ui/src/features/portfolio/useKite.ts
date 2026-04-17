import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import type { KiteStatus } from '@/lib/types';

export function useKiteStatus() {
  return useQuery<KiteStatus, APIError>({
    queryKey: ['kite', 'status'],
    queryFn: () => apiClient.get<KiteStatus>(endpoints.kiteStatus),
    staleTime: 60_000,
    retry: (count, err) => (isNotImplemented(err) ? false : count < 1),
  });
}

interface AuthUrlResponse {
  url: string;
}

// Fetch on demand (button click) — don't prefetch on mount.
export function useKiteAuthUrl() {
  return useMutation<AuthUrlResponse, APIError, void>({
    mutationFn: () => apiClient.get<AuthUrlResponse>(endpoints.kiteAuthUrl),
  });
}
