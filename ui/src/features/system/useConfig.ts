import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { endpoints } from '@/lib/api/endpoints';

// Backend `/config` returns dicts keyed by module; shape isn't in our contracts
// because it's a direct YAML dump. Type loosely — the Settings page reads
// specific keys and defends against missing ones.
export interface ConfigSnapshot {
  data: Record<string, unknown>;
  processing: Record<string, unknown>;
  news: Record<string, unknown>;
  llm: Record<string, unknown> | null;
  api: Record<string, unknown>;
}

export function useConfig() {
  return useQuery<ConfigSnapshot>({
    queryKey: ['config'],
    queryFn: () => apiClient.get<ConfigSnapshot>(endpoints.config),
    staleTime: 60_000,
  });
}
