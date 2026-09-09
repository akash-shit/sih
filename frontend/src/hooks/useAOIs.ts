import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AOI, TimelineEntry, Mosaic } from '@/types/api';

export function useAOIs() {
  return useQuery<AOI[]>({
    queryKey: ['aois'],
    queryFn: () => api.get<AOI[]>('/aois'),
    staleTime: 30000,
  });
}

export function useAOITimeline(aoiId: string | undefined) {
  return useQuery<TimelineEntry[]>({
    queryKey: ['aoi-timeline', aoiId],
    queryFn: () => api.get<TimelineEntry[]>(`/aois/${aoiId}/timeline`),
    enabled: Boolean(aoiId),
    staleTime: 30000,
  });
}

export function useMosaic(aoiId: string | undefined, date: string | undefined) {
  return useQuery<Mosaic>({
    queryKey: ['aoi-mosaic', aoiId, date],
    queryFn: () => api.get<Mosaic>(`/aois/${aoiId}/mosaic`, { date }),
    enabled: Boolean(aoiId && date),
    staleTime: 60000,
  });
}
