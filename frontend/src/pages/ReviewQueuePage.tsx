import React, { useState, useEffect } from 'react';
import { useChangeCandidates, useSubmitDecision } from '@/hooks/useChanges';
import { useAuditLog } from '@/hooks/useAuditLog';
import { GlassPanel } from '@/components/common/GlassPanel';
import { BeforeAfterCompare } from '@/components/common/BeforeAfterCompare';
import { ImageZoomModal } from '@/components/common/ImageZoomModal';
import { ChangeTypeBadge } from '@/components/common/ChangeTypeBadge';
import { MiniBar } from '@/components/common/MiniBar';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatDateTime, formatPercent } from '@/lib/utils';
import type { ChangeCandidate } from '@/types/api';
import { toast } from 'sonner';
import {
  CheckCircle2,
  XCircle,
  History,
} from 'lucide-react';
import { motion } from 'framer-motion';

const priorityBadge = (score: number | null | undefined) => {
  if (score == null || !Number.isFinite(score)) return null;
  const tier = score >= 0.75 ? 'HIGH' : score >= 0.45 ? 'MEDIUM' : 'LOW';
  const styles = tier === 'HIGH'
    ? 'text-rose-300 bg-rose-500/10 border-rose-500/30'
    : tier === 'MEDIUM'
      ? 'text-amber-300 bg-amber-500/10 border-amber-500/30'
      : 'text-sky-300 bg-sky-500/10 border-sky-500/30';
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${styles}`} title={`Strategic priority: ${score.toFixed(2)}`}>
      Priority {tier} · {score.toFixed(2)}
    </span>
  );
};

export const ReviewQueuePage: React.FC = () => {
  const [sort, setSort] = useState<'combined_score' | 'priority' | 'learned'>('combined_score');
  const [activeTab, setActiveTab] = useState<'ALL' | 'OPEN' | 'CONFIRMED' | 'REJECTED' | 'SUPPRESSED' | 'audit'>('OPEN');
  const {
    data: candidates,
    isLoading: candidatesLoading,
    isError: candidatesError,
    refetch: refetchCandidates,
  } = useChangeCandidates(activeTab === 'audit' ? undefined : activeTab, undefined, sort);

  const { data: auditLogs, isLoading: auditLoading } = useAuditLog();
  const submitDecision = useSubmitDecision();

  const [selectedCandidate, setSelectedCandidate] = useState<ChangeCandidate | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [zoomImage, setZoomImage] = useState<string | null>(null);

  // Sync selected candidate when list loads
  useEffect(() => {
    if (candidates && candidates.length > 0) {
      if (!selectedCandidate || !candidates.find((c) => c.candidate_id === selectedCandidate.candidate_id)) {
        setSelectedCandidate(candidates[0]);
      }
    } else {
      setSelectedCandidate(null);
    }
  }, [candidates]);

  const handleDecision = (decision: 'CONFIRM' | 'REJECT') => {
    if (!selectedCandidate) return;

    submitDecision.mutate(
      {
        candidateId: selectedCandidate.candidate_id,
        payload: {
          decision,
          reason: decisionReason || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(`Candidate #${selectedCandidate.candidate_id} ${decision.toLowerCase()}ed!`);
          setDecisionReason('');
          refetchCandidates();
        },
        onError: (err) => {
          toast.error('Failed to submit review decision', {
            description: err.message,
          });
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Analyst Triage & Review Queue
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Human-in-the-Loop decision verification for high-confidence change anomalies
          </p>
        </div>
        <div className="flex gap-2 text-xs font-mono">
          {(['combined_score', 'priority', 'learned'] as const).map((value) => (
            <button key={value} onClick={() => setSort(value)} className={`px-2 py-1 rounded border ${sort === value ? 'border-aurora-400 text-aurora-300' : 'border-white/[0.1] text-text-muted'}`}>
              {value === 'combined_score' ? 'Confidence' : value === 'priority' ? 'Strategic Priority' : 'AI-learned'}
            </button>
          ))}
        </div>

        {/* View Toggle */}
        <div className="flex flex-wrap items-center gap-1 p-1 rounded-xl bg-space-950/60 border border-white/[0.06] self-start font-mono text-xs">
          {(['ALL', 'OPEN', 'CONFIRMED', 'REJECTED', 'SUPPRESSED'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setActiveTab(status)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${activeTab === status ? 'bg-aurora-500/20 text-aurora-300 border border-aurora-500/30' : 'text-text-muted hover:text-text-primary'}`}
            >
              {status} {activeTab === status ? `(${candidates?.length || 0})` : ''}
            </button>
          ))}
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-3 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition-all ${
              activeTab === 'audit'
                ? 'bg-aurora-500/20 text-aurora-300 border border-aurora-500/30'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <History size={14} />
            Audit ({auditLogs?.length || 0})
          </button>
        </div>
      </div>

      {candidatesError && (
        <ErrorCard
          title="Queue Inaccessible"
          message="Could not connect to the review queue endpoint."
          onRetry={() => refetchCandidates()}
        />
      )}

      {activeTab !== 'audit' ? (
        candidatesLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} lines={2} />
              ))}
            </div>
            <div className="lg:col-span-7">
              <SkeletonCard lines={8} hasThumbnail />
            </div>
          </div>
        ) : !candidates || candidates.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="Review Queue Clear"
            description="All pending change candidates have been reviewed by analysts. Check back after next pipeline ingestion."
          />
        ) : (
          /* Split View: Left List of Candidates, Right Decision Panel */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Scrollable List */}
            <div className="lg:col-span-5 space-y-3 max-h-[750px] overflow-y-auto pr-1">
              {candidates.map((cand) => {
                const isSelected = selectedCandidate?.candidate_id === cand.candidate_id;

                return (
                  <GlassPanel
                    key={cand.candidate_id}
                    hoverEffect
                    onClick={() => setSelectedCandidate(cand)}
                    className={`p-3.5 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-aurora-400 bg-aurora-500/10 shadow-glow-cyan/20'
                        : 'hover:border-white/[0.15]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-text-primary">
                          #{cand.candidate_id}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.04] text-text-secondary border border-white/[0.08] capitalize">
                          {cand.aoi_name || cand.aoi_id}
                        </span>
                      </div>
                      <span className="font-mono text-xs font-bold text-aurora-300">
                        {formatPercent(cand.combined_score)}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-text-muted mb-2">
                      <span>Tile: {cand.tile_id}</span>
                      <span className="text-right">
                        {formatDate(cand.before_date)} → {formatDate(cand.after_date)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-white/[0.06]">
                      <ChangeTypeBadge type={cand.change_type} size="sm" />
                      {priorityBadge(cand.priority_score)}
                      {cand.sar_only ? <span className="text-[10px] text-amber-300">SAR-ONLY</span> : cand.fused_score != null ? <span className="text-[10px] text-cyan-300">SAR-FUSED</span> : null}
                      {cand.land_cover ? <span className="text-[10px] text-emerald-300">{cand.land_cover}</span> : null}
                      <span className="text-[10px] font-mono text-text-muted">
                        Drift: {cand.embedding_drift?.toFixed(2)}
                      </span>
                    </div>
                  </GlassPanel>
                );
              })}
            </div>

            {/* Right Detailed Inspector & Fast Decision Bar */}
            <div className="lg:col-span-7">
              {selectedCandidate ? (
                <GlassPanel className="p-6 space-y-6">
                  {/* Candidate Title Header */}
                  <div className="flex items-start justify-between pb-4 border-b border-white/[0.06]">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold font-mono text-text-primary">
                          Candidate #{selectedCandidate.candidate_id}
                        </h2>
                        <ChangeTypeBadge type={selectedCandidate.change_type} />
                        {priorityBadge(selectedCandidate.priority_score)}
                      </div>
                      <p className="text-xs font-mono text-text-muted mt-0.5">
                        Tile ID: {selectedCandidate.tile_id} · AOI: {selectedCandidate.aoi_name || selectedCandidate.aoi_id}
                      </p>
                    </div>

                    <div className="text-right font-mono">
                      <span className="text-[10px] uppercase text-text-muted block">Score</span>
                      <span className="text-xl font-bold text-aurora-300">
                        {formatPercent(selectedCandidate.combined_score)}
                      </span>
                    </div>
                  </div>

                  {/* Before/After Images */}
                  <BeforeAfterCompare
                    beforeUrl={selectedCandidate.before_thumbnail_url}
                    afterUrl={selectedCandidate.after_thumbnail_url}
                    beforeDate={selectedCandidate.before_date}
                    afterDate={selectedCandidate.after_date}
                    defaultMode="slider"
                  />
                  <ImageZoomModal
                    src={zoomImage ?? undefined}
                    alt="Satellite imagery detail"
                    open={Boolean(zoomImage)}
                    onClose={() => setZoomImage(null)}
                  />

                  {/* Scores Progress Bars */}
                  <div className="space-y-2 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                    <MiniBar
                      label="Semantic Drift (ViT-B-32 Distance)"
                      value={selectedCandidate.embedding_drift}
                      color="cyan"
                    />
                    <MiniBar
                      label="Spectral Delta (Band 4-8 Difference)"
                      value={selectedCandidate.spectral_delta}
                      color="violet"
                    />
                    <MiniBar
                      label="Combined Anomaly Confidence"
                      value={selectedCandidate.combined_score}
                      color="gradient"
                    />
                  </div>

                  {/* Decision Controls */}
                  {selectedCandidate.status === 'OPEN' && <div className="pt-4 border-t border-white/[0.06] space-y-4">
                    <div>
                      <label className="block text-[11px] font-mono uppercase text-text-muted mb-1.5">
                        Analyst Verification Note (Optional)
                      </label>
                      <input
                        type="text"
                        value={decisionReason}
                        onChange={(e) => setDecisionReason(e.target.value)}
                        placeholder="e.g. Ground cleared for new infrastructure project"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.1] text-xs font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleDecision('CONFIRM')}
                        disabled={submitDecision.isPending}
                        className="flex-1 py-3 rounded-xl font-mono text-xs font-bold uppercase tracking-wider bg-emerald-500 hover:bg-emerald-400 text-space-950 shadow-glow-emerald/20 transition-all flex items-center justify-center gap-2"
                      >
                        <CheckCircle2 size={16} />
                        Confirm Change
                      </button>
                      <button
                        onClick={() => handleDecision('REJECT')}
                        disabled={submitDecision.isPending}
                        className="flex-1 py-3 rounded-xl font-mono text-xs font-bold uppercase tracking-wider bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 transition-all flex items-center justify-center gap-2"
                      >
                        <XCircle size={16} />
                        Reject (False Positive)
                      </button>
                    </div>
                  </div>}
                </GlassPanel>
              ) : (
                <GlassPanel className="p-12 text-center text-text-muted text-xs font-mono">
                  Select a candidate from the left list to review evidence.
                </GlassPanel>
              )}
            </div>
          </div>
        )
      ) : (
        /* Audit Trail Table */
        <GlassPanel className="p-5">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-white/[0.08] text-text-muted uppercase text-[10px]">
                  <th className="pb-3 px-3">Log ID</th>
                  <th className="pb-3 px-3">Candidate</th>
                  <th className="pb-3 px-3">Tile</th>
                  <th className="pb-3 px-3">Decision</th>
                  <th className="pb-3 px-3">Reason / Audit Rationale</th>
                  <th className="pb-3 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {auditLoading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-muted">
                      Loading audit entries…
                    </td>
                  </tr>
                ) : !auditLogs || auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-muted">
                      No analyst decisions recorded in audit log yet.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((entry, index) => (
                    <motion.tr
                      key={entry.log_id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className="hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="py-3 px-3 text-text-muted">#{entry.log_id}</td>
                      <td className="py-3 px-3 text-text-primary font-semibold">
                        #{entry.candidate_id}
                      </td>
                      <td className="py-3 px-3 text-text-secondary">{entry.tile_id || '—'}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            entry.decision.toLowerCase() === 'confirm'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {entry.decision}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-text-secondary max-w-xs truncate">
                        {entry.reason || '—'}
                      </td>
                      <td className="py-3 px-3 text-text-muted">{formatDateTime(entry.created_at)}</td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </GlassPanel>
      )}
    </div>
  );
};
