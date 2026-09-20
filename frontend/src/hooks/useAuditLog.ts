import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AuditLogEntry } from '@/types/api';

export function useAuditLog(enabled = true) {
  return useQuery<AuditLogEntry[]>({
    queryKey: ['audit-log'],
    queryFn: () => api.get<AuditLogEntry[]>('/review/audit-log'),
    enabled,
    staleTime: 15000,
  });
}
