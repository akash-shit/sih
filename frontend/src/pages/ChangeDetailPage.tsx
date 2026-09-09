import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChangeDetail, useSubmitDecision } from '@/hooks/useChanges';
import { GlassPanel } from '@/components/common/GlassPanel';
import { BeforeAfterCompare } from '@/components/common/BeforeAfterCompare';
import { ImageZoomModal } from '@/components/common/ImageZoomModal';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ChangeTypeBadge } from '@/components/common/ChangeTypeBadge';
import { NDVIChart } from '@/components/common/NDVIChart';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatPercent, formatCoord } from '@/lib/utils';
import { toast } from 'sonner';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Activity,
  AlertCircle,
  Layers,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react';
import { motion } from 'framer-motion';

export const ChangeDetailPage: React.FC = () => {
  const { vectorId } = useParams<{ vectorId: string }>();
  const navigate = useNavigate();

  const { data: change, isLoading, isError, refetch } = useChangeDetail(vectorId);
  const submitDecision = useSubmitDecision();

  const [decisionReason, setDecisionReason] = useState('');
  const [activeModal, setActiveModal] = useState<'CONFIRM' | 'REJECT' | null>(null);
  const [zoomImage, setZoomImage] = useState<string | null>(null);
  const [isCompareFullscreen, setIsCompareFullscreen] = useState(false);

  useEffect(() => {
    if (!isCompareFullscreen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsCompareFullscreen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCompareFullscreen]);

  const handleAction = (decision: 'CONFIRM' | 'REJECT') => {
    if (!change) return;

    submitDecision.mutate(
      {
        candidateId: change.candidate_id,
        payload: {
          decision,
          reason: decisionReason || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(`Change candidate #${change.candidate_id} marked as ${decision}`, {
            description: decisionReason ? `Reason: ${decisionReason}` : undefined,
          });
          setActiveModal(null);
          setDecisionReason('');
          refetch();
        },
        onError: (err) => {
          toast.error('Failed to register review decision', {
            description: err.message,
          });
        },
      }
    );
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary hover:text-text-primary border border-white/[0.08] transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl lg:text-2xl font-bold tracking-tight text-text-primary">
                Candidate Evidence #{change?.candidate_id || vectorId}
              </h1>
              {change && <StatusBadge status={change.status} />}
            </div>
            <p className="text-xs text-text-secondary mt-0.5 font-mono">
              Tile Ground Footprint: {change?.tile_id || '—'}
            </p>
          </div>
        </div>

        {/* Quick Review Actions if status is OPEN */}
        {change && change.status === 'OPEN' && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveModal('CONFIRM')}
              className="px-4 py-2 rounded-xl text-xs font-mono font-medium bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 shadow-glow-emerald/20 transition-all flex items-center gap-2"
            >
              <CheckCircle2 size={14} />
              Confirm Change
            </button>
            <button
              onClick={() => setActiveModal('REJECT')}
              className="px-4 py-2 rounded-xl text-xs font-mono font-medium bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 shadow-glow-rose/20 transition-all flex items-center gap-2"
            >
              <XCircle size={14} />
              Reject Change
            </button>
          </div>
        )}
      </div>

      {isError && (
        <ErrorCard
          title="Failed to Load Candidate Detail"
          message="Could not retrieve spectral evidence or temporal history for this vector ID."
          onRetry={() => refetch()}
        />
      )}

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkeletonCard hasThumbnail lines={2} />
            <SkeletonCard hasThumbnail lines={2} />
            <SkeletonCard hasThumbnail lines={2} />
          </div>
          <SkeletonCard lines={8} />
        </div>
      ) : change && (
        <>
          {/* Section 1: Before / After / Difference Triptych */}
          <div className="space-y-3">
            <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
              <Layers size={14} className="text-aurora-400" />
              Multi-Temporal Sensor Triptych Inspection
            </h2>

            <GlassPanel className="relative w-full max-w-4xl mx-auto p-5">
              <BeforeAfterCompare
                beforeUrl={change.before_image_url}
                afterUrl={change.after_image_url}
                differenceUrl={change.evidence?.difference_image_url}
                beforeDate={change.before_date}
                afterDate={change.after_date}
                defaultMode="slider"
                onFullscreen={() => setIsCompareFullscreen(true)}
              />
            </GlassPanel>

            {isCompareFullscreen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-space-950/90 p-3 backdrop-blur-sm">
                <GlassPanel className="relative h-full w-full max-w-7xl p-4 bg-space-900/95">
                  <button
                    type="button"
                    aria-label="Close fullscreen comparison"
                    onClick={() => setIsCompareFullscreen(false)}
                    className="absolute right-5 top-5 z-20 flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.12] bg-space-950/80 text-text-secondary transition hover:text-text-primary"
                  >
                    <X size={16} />
                  </button>
                  <BeforeAfterCompare
                    beforeUrl={change.before_image_url}
                    afterUrl={change.after_image_url}
                    differenceUrl={change.evidence?.difference_image_url}
                    beforeDate={change.before_date}
                    afterDate={change.after_date}
                    defaultMode="slider"
                    fullBleed
                    onFullscreen={() => setIsCompareFullscreen(false)}
                  />
                </GlassPanel>
              </div>
            )}

            <ImageZoomModal
              src={zoomImage ?? undefined}
              alt="Satellite imagery detail"
              open={Boolean(zoomImage)}
              onClose={() => setZoomImage(null)}
            />
          </div>

          {/* Section 2: Spectral Evidence & Interpretation Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <GlassPanel className="p-6 lg:col-span-2 space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
                  <Activity size={14} className="text-aurora-400" />
                  Analytic Synthesis & Visual Difference Summary
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-white/[0.05] text-text-secondary border border-white/[0.08]">
                  Quality: {change.evidence?.quality || 'evaluated'}
                </span>
              </div>

              {/* Visual difference summary */}
              <p className="text-sm text-text-primary leading-relaxed bg-white/[0.02] border border-white/[0.06] p-4 rounded-xl font-mono text-xs">
                {change.evidence?.visual_difference_summary}
              </p>

              <p className="text-sm text-text-secondary leading-relaxed font-mono text-xs">
                {change.evidence?.narrative}
              </p>

              {/* Multi-spectral metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    NDVI Shift (Δ)
                  </span>
                  <div className="flex items-center gap-1.5 mt-1">
                    {change.evidence?.ndvi_change && change.evidence.ndvi_change < 0 ? (
                      <TrendingDown size={16} className="text-rose-400" />
                    ) : (
                      <TrendingUp size={16} className="text-emerald-400" />
                    )}
                    <span
                      className={`text-lg font-mono font-bold ${
                        change.evidence?.ndvi_change && change.evidence.ndvi_change < 0
                          ? 'text-rose-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      {change.evidence?.ndvi_change !== null
                        ? change.evidence?.ndvi_change?.toFixed(3)
                        : '—'}
                    </span>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    Spectral Delta
                  </span>
                  <span className="text-lg font-mono font-bold text-violet-light mt-1 block">
                    {change.spectral_delta?.toFixed(3) ?? '—'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    Semantic Drift
                  </span>
                  <span className="text-lg font-mono font-bold text-aurora-400 mt-1 block">
                    {change.embedding_drift?.toFixed(3) ?? '—'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    Combined Score
                  </span>
                  <span className="text-lg font-mono font-bold text-text-primary mt-1 block">
                    {formatPercent(change.combined_score)}
                  </span>
                </div>
              </div>

              {/* Classification inference */}
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-aurora-500/10 text-aurora-400 border border-aurora-500/20">
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-text-muted block">
                      Zero-Shot CLIP Classification
                    </span>
                    <p className="text-xs font-mono font-semibold text-text-primary">
                      {change.evidence?.candidate_interpretation || 'Unclassified Anomaly'}
                    </p>
                  </div>
                </div>
                <ChangeTypeBadge type={change.change_type} />
              </div>
            </GlassPanel>

            {/* Side Panel: Confound & Physical Provenance */}
            <GlassPanel className="p-6 space-y-5">
              <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
                <AlertCircle size={14} className="text-amber-400" />
                Confound Analysis & Radiometry
              </h3>

              <div className="space-y-2">
                {change.quality_notes?.map((note, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06] text-xs font-mono text-text-secondary flex items-center justify-between"
                  >
                    <span>{note.split(':')[0]}</span>
                    <span className="text-text-primary font-medium">{note.split(':')[1] || ''}</span>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-white/[0.06] space-y-2 text-xs font-mono text-text-muted">
                <div className="flex items-center justify-between">
                  <span>Centroid Lat/Lon:</span>
                  <span className="text-text-primary">
                    {formatCoord(change.lat)}, {formatCoord(change.lon)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Provenance Source:</span>
                  <span className="text-text-primary">{change.acquisition_date_source || 'JSON Tag'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Pipeline Build:</span>
                  <span className="text-text-primary">{change.processing_version || 'v0.1'}</span>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* Section 3: Multi-Temporal NDVI / NDWI Time Series Chart */}
          <GlassPanel className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
                  <Activity size={14} className="text-emerald-400" />
                  Historical Multi-Temporal NDVI & NDWI Trajectory
                </h3>
                <p className="text-[11px] font-mono text-text-muted mt-0.5">
                  Pre- and post-event spectral indices across all ingested Sentinel-2 scenes
                </p>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs">
                <span className="text-text-muted">
                  T1: <span className="text-text-primary">{formatDate(change.before_date)}</span>
                </span>
                <span className="text-text-muted">
                  T2: <span className="text-aurora-300">{formatDate(change.after_date)}</span>
                </span>
              </div>
            </div>

            <NDVIChart
              series={change.ndvi_series || []}
              beforeDate={change.before_date}
              afterDate={change.after_date}
            />
          </GlassPanel>
        </>
      )}

      {/* Decision Modal / Confirmation Dialog */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-space-950/80 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-md"
          >
            <GlassPanel
              glowColor={activeModal === 'CONFIRM' ? 'emerald' : 'rose'}
              className="p-6 space-y-4 border-white/[0.12] bg-space-900 shadow-2xl"
            >
              <h3 className="text-sm font-semibold text-text-primary font-mono flex items-center gap-2">
                {activeModal === 'CONFIRM' ? (
                  <>
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    Confirm Satellite Change Candidate
                  </>
                ) : (
                  <>
                    <XCircle size={16} className="text-rose-400" />
                    Reject Change (Mark False Positive)
                  </>
                )}
              </h3>

              <p className="text-xs text-text-secondary leading-relaxed">
                {activeModal === 'CONFIRM'
                  ? 'Confirming registers this candidate as a verified ground change in the audit trail, promoting it for intelligence reporting.'
                  : 'Rejecting marks this candidate as a false alarm or confound, suppressing it from priority queues.'}
              </p>

              <div>
                <label className="block text-[10px] font-mono uppercase text-text-muted mb-1.5">
                  Analyst Rationale / Evidence Note (Optional)
                </label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="e.g. Verified against high-res optical pass or ground survey data"
                  rows={3}
                  className="w-full p-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-xs font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-4 py-2 rounded-xl text-xs font-mono text-text-muted hover:text-text-primary transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleAction(activeModal)}
                  disabled={submitDecision.isPending}
                  className={`px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all shadow-glass flex items-center gap-2 ${
                    activeModal === 'CONFIRM'
                      ? 'bg-emerald-500 hover:bg-emerald-400 text-space-950 shadow-glow-emerald/30'
                      : 'bg-rose-500 hover:bg-rose-400 text-white shadow-glow-rose/30'
                  }`}
                >
                  {submitDecision.isPending ? 'Logging…' : `Submit ${activeModal}`}
                </button>
              </div>
            </GlassPanel>
          </motion.div>
        </div>
      )}
    </div>
  );
};
