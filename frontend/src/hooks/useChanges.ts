import { keepPreviousData, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  ChangeCandidate,
  ChangeDetail,
  ReviewQuality,
  ReviewDecision,
  ReviewResponse,
} from '@/types/api';

export function useChangeCandidates(status?: string, aoiId?: string) {
  return useQuery<ChangeCandidate[]>({
    queryKey: ['change-candidates', status, aoiId],
    queryFn: ({ signal }) =>
      api.get<ChangeCandidate[]>('/changes/candidates', {
        status: status && status !== 'ALL' ? status : undefined,
        aoi_id: aoiId || undefined,
        limit: 24,
      }, signal),
    staleTime: 30000,
    gcTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useDataQuality() {
  return useQuery<ReviewQuality>({
    queryKey: ['data-quality'],
    queryFn: ({ signal }) => api.get<ReviewQuality>('/changes/candidates/data-quality', undefined, signal),
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

export function useChangeDetail(vectorId: string | number | undefined) {
  return useQuery<ChangeDetail>({
    queryKey: ['change-detail', vectorId],
    queryFn: ({ signal }) => api.get<ChangeDetail>(`/changes/${vectorId}`, undefined, signal),
    enabled: Boolean(vectorId),
    staleTime: 30000,
  });
}

export function useSubmitDecision() {
  const queryClient = useQueryClient();

  return useMutation<ReviewResponse, Error, { candidateId: string; payload: ReviewDecision }>({
    mutationFn: ({ candidateId, payload }) =>
      api.post<ReviewResponse>(`/review/${candidateId}/decision`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['change-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['change-detail'] });
      queryClient.invalidateQueries({ queryKey: ['audit-log'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}
