import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AuditLogEntry } from '@/types/api';

export function useAuditLog() {
  return useQuery<AuditLogEntry[]>({
    queryKey: ['audit-log'],
    queryFn: () => api.get<AuditLogEntry[]>('/review/audit-log'),
    staleTime: 15000,
  });
}
