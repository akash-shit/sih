import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { OnboardJob } from '@/types/api';

export interface StartOnboardPayload {
  name: string;
  source_folder: string;
}

export function useStartOnboard() {
  return useMutation<OnboardJob, Error, StartOnboardPayload>({
    mutationFn: (payload) => api.post<OnboardJob>('/aois/onboard', payload),
  });
}

export function useOnboardJob(jobId: string | undefined | null) {
  return useQuery<OnboardJob>({
    queryKey: ['onboard-job', jobId],
    queryFn: () => api.get<OnboardJob>(`/aois/onboard/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'queued' || status === 'running') {
        return 2000;
      }
      return false;
    },
  });
}
