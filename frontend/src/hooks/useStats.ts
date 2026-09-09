import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Stats } from '@/types/api';

export function useStats() {
  return useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: () => api.get<Stats>('/stats'),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}
