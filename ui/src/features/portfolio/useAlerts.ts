import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { APIError } from '@/lib/api/errors';
import { endpoints } from '@/lib/api/endpoints';
import { isNotImplemented } from '@/lib/api/isNotImplemented';
import type { Alert, AlertRule, AlertType } from '@/lib/types';

export function useAlerts() {
  return useQuery<Alert[], APIError>({
    queryKey: ['portfolio', 'alerts'],
    queryFn: () => apiClient.get<Alert[]>(endpoints.portfolioAlerts),
    staleTime: 60_000,
    retry: (count, err) => (isNotImplemented(err) ? false : count < 1),
  });
}

export interface NewAlertRule {
  type: AlertType;
  symbol: string | null;
  threshold: number;
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation<AlertRule, APIError, NewAlertRule>({
    mutationFn: (body) => apiClient.post<AlertRule>(endpoints.portfolioAlerts, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portfolio', 'alerts'] });
    },
  });
}

export function useDeleteAlertRule() {
  const qc = useQueryClient();
  return useMutation<void, APIError, string>({
    mutationFn: (id) => apiClient.delete<void>(endpoints.portfolioAlert(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portfolio', 'alerts'] });
    },
  });
}
