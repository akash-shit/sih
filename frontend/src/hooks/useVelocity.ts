import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { VelocityTile } from '@/types/api';

export function useVelocity(limit = 8) {
  return useQuery<VelocityTile[]>({
    queryKey: ['velocity', limit],
    queryFn: ({ signal }) => api.get<VelocityTile[]>('/changes/velocity', { limit }, signal),
    staleTime: 60000,
    gcTime: 10 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}