import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { VelocityTile } from '@/types/api';

export function useVelocity() {
  return useQuery<VelocityTile[]>({
    queryKey: ['velocity'],
    queryFn: ({ signal }) => api.get<VelocityTile[]>('/changes/velocity', undefined, signal),
    staleTime: 30000,
  });
}