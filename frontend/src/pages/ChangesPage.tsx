import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChangeCandidates, useDataQuality } from '@/hooks/useChanges';
import { useAOIs } from '@/hooks/useAOIs';
import { GlassPanel } from '@/components/common/GlassPanel';
import { BeforeAfterCompare } from '@/components/common/BeforeAfterCompare';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ChangeTypeBadge } from '@/components/common/ChangeTypeBadge';
import { MiniBar } from '@/components/common/MiniBar';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatPercent } from '@/lib/utils';
import type { ChangeStatus } from '@/types/api';
import { Radar, ArrowRight, Filter, AlertTriangle, ShieldCheck } from 'lucide-react';

const statuses: (ChangeStatus | 'ALL')[] = [
  'ALL',
  'OPEN',
  'CONFIRMED',
  'REJECTED',
  'SUPPRESSED',
];

export const ChangesPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedStatus, setSelectedStatus] = useState<ChangeStatus | 'ALL'>('ALL');
  const [selectedAoi, setSelectedAoi] = useState<string>('');

  const {
    data: candidates,
    isLoading,
    isError,
    refetch,
  } = useChangeCandidates(selectedStatus, selectedAoi);

  const { data: quality } = useDataQuality();
  const { data: aois } = useAOIs();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Change Detection Surveillance
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Zero-shot semantic drift paired with multi-spectral delta scoring
          </p>
        </div>

        {/* Data Quality Counters */}
        {quality && (
          <div className="flex items-center gap-2 self-start sm:self-auto font-mono text-xs">
            <div className="px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-2">
              <ShieldCheck size={14} className="text-aurora-400" />
              <span className="text-text-secondary">Displayable:</span>
              <span className="text-text-primary font-bold">
                {quality.displayable_candidates}
              </span>
            </div>
            <div className="px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-400" />
              <span className="text-text-secondary">Excluded (Source Missing):</span>
              <span className="text-amber-300 font-bold">
                {quality.source_imagery_unavailable}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <GlassPanel className="p-3 sm:p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Status Segmented Control */}
        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto p-1 rounded-xl bg-space-950/60 border border-white/[0.06]">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setSelectedStatus(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                selectedStatus === s
                  ? 'bg-aurora-500/20 text-aurora-300 border border-aurora-500/30 shadow-glow-cyan/10'
                  : 'text-text-muted hover:text-text-primary hover:bg-white/[0.04]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* AOI Dropdown */}
        <div className="flex items-center gap-2 w-full md:w-auto self-end">
          <Filter size={14} className="text-text-muted" />
          <select
            value={selectedAoi}
            onChange={(e) => setSelectedAoi(e.target.value)}
            className="w-full md:w-48 bg-space-850 border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-text-primary font-mono focus:outline-none focus:border-aurora-400"
          >
            <option value="">All AOIs</option>
            {aois?.map((aoi) => (
              <option key={aoi.aoi_id} value={aoi.aoi_id}>
                {aoi.name}
              </option>
            ))}
          </select>
        </div>
      </GlassPanel>

      {isError && (
        <ErrorCard
          title="Failed to Load Change Candidates"
          message="Could not retrieve candidate anomaly pairs from the change detection engine."
          onRetry={() => refetch()}
        />
      )}

      {/* Grid of Candidates */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 change-candidate-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} lines={5} hasThumbnail />
          ))}
        </div>
      ) : !candidates || candidates.length === 0 ? (
        <EmptyState
          icon={Radar}
          title="No Change Candidates Found"
          description={`No candidates matched the current filter parameters (Status: ${selectedStatus}, AOI: ${selectedAoi || 'All'}).`}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 change-candidate-grid">
          {candidates.map((cand) => {
            const vectorId = cand.vector_id ?? cand.candidate_id;

            return (
              <div
                key={cand.candidate_id}
              >
                <GlassPanel
                  hoverEffect
                  onClick={() => navigate(`/changes/${vectorId}`)}
                  className="p-5 cursor-pointer space-y-4 group flex flex-col justify-between h-full"
                >
                  {/* Top Header: IDs & Status Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-text-primary">
                          Candidate #{cand.candidate_id}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.04] text-text-secondary border border-white/[0.06] capitalize">
                          {cand.aoi_name || cand.aoi_id}
                        </span>
                      </div>
                      <p className="font-mono text-[11px] text-text-muted mt-0.5">
                        Tile: {cand.tile_id}
                      </p>
                    </div>
                    <StatusBadge status={cand.status} size="sm" />
                  </div>

                  {/* Shared before/after slider */}
                  <BeforeAfterCompare
                    beforeUrl={cand.before_thumbnail_url}
                    afterUrl={cand.after_thumbnail_url}
                    beforeDate={cand.before_date}
                    afterDate={cand.after_date}
                    defaultMode="slider"
                  />

                  {/* Temporal interval */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-text-secondary border-t border-white/[0.06] pt-2">
                    <span>{formatDate(cand.before_date)}</span>
                    <ArrowRight size={11} className="text-text-muted" />
                    <span className="text-text-primary font-medium">{formatDate(cand.after_date)}</span>
                  </div>

                  {cand.source_unavailable_reason && (
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[10px] font-mono text-amber-200">
                      Source imagery unavailable. This candidate is excluded from normal visual review.
                    </div>
                  )}

                  {/* Score Breakdown Bars */}
                  <div className="space-y-2 pt-1">
                    <MiniBar
                      label="Semantic Embedding Drift"
                      value={cand.embedding_drift}
                      color="cyan"
                    />
                    <MiniBar
                      label="Multi-Spectral Delta"
                      value={cand.spectral_delta}
                      color="violet"
                    />
                    <MiniBar
                      label="Combined Anomaly Score"
                      value={cand.combined_score}
                      color="gradient"
                    />
                  </div>

                  {/* Change classification & Footer */}
                  <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between">
                    <ChangeTypeBadge type={cand.change_type} size="sm" />
                    {cand.confidence !== null && cand.confidence !== undefined && (
                      <span className="text-[11px] font-mono text-text-muted">
                        Conf: {formatPercent(cand.confidence)}
                      </span>
                    )}
                  </div>

                  {/* Suppression Alert Callout if applicable */}
                  {cand.suppressed && cand.suppression_reason && (
                    <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[10px] font-mono text-rose-300 flex items-center gap-1.5">
                      <AlertTriangle size={12} className="shrink-0 text-rose-400" />
                      <span className="truncate">{cand.suppression_reason}</span>
                    </div>
                  )}
                </GlassPanel>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
