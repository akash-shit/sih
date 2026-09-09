import React, { useState, useMemo } from 'react';
import { useAuditLog } from '@/hooks/useAuditLog';
import { GlassPanel } from '@/components/common/GlassPanel';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDateTime } from '@/lib/utils';
import { Search, ArrowUpDown, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { motion } from 'framer-motion';

export const AuditLogPage: React.FC = () => {
  const { data: logs, isLoading, isError, refetch } = useAuditLog();

  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  // Search & sort filtered entries
  const filteredLogs = useMemo(() => {
    if (!logs) return [];
    let list = [...logs];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (entry) =>
          entry.log_id.toLowerCase().includes(q) ||
          entry.candidate_id.toLowerCase().includes(q) ||
          (entry.tile_id && entry.tile_id.toLowerCase().includes(q)) ||
          entry.decision.toLowerCase().includes(q) ||
          (entry.reason && entry.reason.toLowerCase().includes(q))
      );
    }

    list.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });

    return list;
  }, [logs, searchQuery, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / pageSize));
  const paginatedLogs = filteredLogs.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const exportCSV = () => {
    if (!logs || logs.length === 0) return;
    const headers = 'Log ID,Candidate ID,Tile ID,Decision,Reason,Timestamp\n';
    const rows = filteredLogs
      .map(
        (l) =>
          `"${l.log_id}","${l.candidate_id}","${l.tile_id || ''}","${l.decision}","${(l.reason || '').replace(/"/g, '""')}","${l.created_at}"`
      )
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `skyanalyst-audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Analyst Review Audit Trail
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Cryptographically sealed provenance log of all human verification actions
          </p>
        </div>

        <button
          onClick={exportCSV}
          disabled={!logs || logs.length === 0}
          className="px-3.5 py-2 rounded-xl text-xs font-mono font-medium bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-40 text-text-secondary hover:text-text-primary border border-white/[0.08] transition-all flex items-center gap-2 self-start"
        >
          <Download size={14} />
          Export Audit CSV
        </button>
      </div>

      {/* Table & Filter Container */}
      <GlassPanel className="p-5 space-y-4">
        {/* Search & Sort Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Filter by Candidate ID, Tile, or Rationale…"
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-between font-mono text-xs text-text-muted">
            <span>{filteredLogs.length} entries recorded</span>
            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary border border-white/[0.06] transition-colors"
            >
              <ArrowUpDown size={12} />
              {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
            </button>
          </div>
        </div>

        {isError && (
          <ErrorCard
            title="Audit Trail Inaccessible"
            message="Could not query the SQLite audit log database."
            onRetry={() => refetch()}
          />
        )}

        {/* Data Table */}
        <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-space-950/70 border-b border-white/[0.08] text-text-muted uppercase text-[10px]">
              <tr>
                <th className="py-3 px-4">Log ID</th>
                <th className="py-3 px-4">Candidate</th>
                <th className="py-3 px-4">Tile Footprint</th>
                <th className="py-3 px-4">Decision</th>
                <th className="py-3 px-4">Analyst Verification Rationale</th>
                <th className="py-3 px-4">Timestamp (UTC)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-text-muted">
                    Loading cryptographic audit trail…
                  </td>
                </tr>
              ) : paginatedLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-text-muted">
                    {searchQuery ? 'No audit records match search query.' : 'Zero analyst decisions logged yet.'}
                  </td>
                </tr>
              ) : (
                paginatedLogs.map((entry, index) => (
                  <motion.tr
                    key={entry.log_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.02 }}
                    className="hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="py-3 px-4 text-text-muted">#{entry.log_id}</td>
                    <td className="py-3 px-4 text-text-primary font-bold">
                      #{entry.candidate_id}
                    </td>
                    <td className="py-3 px-4 text-text-secondary">{entry.tile_id || '—'}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          entry.decision.toLowerCase() === 'confirm'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            entry.decision.toLowerCase() === 'confirm'
                              ? 'bg-emerald-400'
                              : 'bg-rose-400'
                          }`}
                        />
                        {entry.decision}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-text-secondary max-w-sm truncate">
                      {entry.reason || '—'}
                    </td>
                    <td className="py-3 px-4 text-text-muted">{formatDateTime(entry.created_at)}</td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-3 font-mono text-xs">
            <span className="text-text-muted">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] disabled:opacity-30 text-text-secondary transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] disabled:opacity-30 text-text-secondary transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </GlassPanel>
    </div>
  );
};
