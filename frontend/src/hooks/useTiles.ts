import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { TileDetail, SearchResult } from '@/types/api';

export function useTile(tileId: string | undefined) {
  return useQuery<TileDetail>({
    queryKey: ['tile', tileId],
    queryFn: () => api.get<TileDetail>(`/tiles/${tileId}`),
    enabled: Boolean(tileId),
    staleTime: 60000,
  });
}

export function useSimilarTiles(tileId: string | undefined, k = 12) {
  return useQuery<SearchResult[]>({
    queryKey: ['tile-similar', tileId, k],
    queryFn: () => api.get<SearchResult[]>(`/tiles/${tileId}/similar`, { k }),
    enabled: Boolean(tileId),
    staleTime: 60000,
  });
}

export function useSimilarTilesByVector(vectorId: number | null | undefined, k = 12) {
  return useQuery<SearchResult[], Error>({
    queryKey: ['similar-tiles-vector', vectorId, k],
    queryFn: () => api.get<SearchResult[]>(`/vectors/${vectorId}/similar`, { k }),
    enabled: vectorId !== null && vectorId !== undefined,
  });
}
