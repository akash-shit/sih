import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Storyline, TemporalSignature } from '@/types/api';

export function useTemporalSignature(tileId: string | undefined) {
  return useQuery<TemporalSignature>({
    queryKey: ['temporal-signature', tileId],
    queryFn: ({ signal }) => api.get<TemporalSignature>(`/tiles/${tileId}/temporal-signature`, undefined, signal),
    enabled: Boolean(tileId),
    staleTime: 30000,
  });
}

export function useStoryline(tileId: string | undefined) {
  return useQuery<Storyline>({
    queryKey: ['storyline', tileId],
    queryFn: ({ signal }) => api.get<Storyline>(`/tiles/${tileId}/storyline`, undefined, signal),
    enabled: Boolean(tileId),
    staleTime: 30000,
  });
}