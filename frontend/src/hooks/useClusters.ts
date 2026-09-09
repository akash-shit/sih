import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Cluster, ClusterMember } from '@/types/api';

export function useClusters() {
  return useQuery<Cluster[]>({
    queryKey: ['clusters'],
    queryFn: () => api.get<Cluster[]>('/clusters'),
    staleTime: 60000,
  });
}

export function useClusterMembers(clusterId: number | string | undefined) {
  return useQuery<ClusterMember[]>({
    queryKey: ['cluster-members', clusterId],
    queryFn: () => api.get<ClusterMember[]>(`/clusters/${clusterId}/members`),
    enabled: Boolean(clusterId !== undefined && clusterId !== ''),
    staleTime: 60000,
  });
}
