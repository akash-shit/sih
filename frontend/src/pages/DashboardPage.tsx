import React from 'react';
import { useStats } from '@/hooks/useStats';
import { StatCard } from '@/components/common/StatCard';
import { GlassPanel } from '@/components/common/GlassPanel';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDateTime } from '@/lib/utils';
import {
  Map,
  Satellite,
  Grid,
  Cpu,
  Radar,
  TrendingUp,
  CheckCircle2,
  ShieldAlert,
  Terminal,
  Activity,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { data: stats, isLoading, isError, refetch } = useStats();

  return (
    <div className="space-y-8 relative">
      {/* Cinematic Horizontal Scan Line */}
      <div className="relative w-full h-[2px] overflow-hidden bg-white/[0.04]">
        <div className="w-48 h-full bg-gradient-to-r from-transparent via-aurora-400 to-transparent animate-scan-line shadow-[0_0_8px_#00D4FF]" />
      </div>

      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-aurora-500/10 border border-aurora-500/20 text-aurora-400 text-[10px] font-mono uppercase tracking-wider mb-2">
            <Activity size={12} className="animate-pulse" />
            Live Geospatial Telemetry
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-text-primary">
            Mission Command Dashboard
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Pipeline Sync:{' '}
            <span className="text-text-primary">
              {stats?.last_run ? formatDateTime(stats.last_run) : 'Real-time feed standby'}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/changes"
            className="px-3.5 py-2 rounded-xl text-xs font-mono font-medium bg-aurora-500/10 hover:bg-aurora-500/20 text-aurora-300 border border-aurora-500/30 transition-all flex items-center gap-2"
          >
            <Radar size={14} />
            Surveillance Feed
          </Link>
          <Link
            to="/onboard"
            className="px-3.5 py-2 rounded-xl text-xs font-mono font-medium bg-gradient-to-r from-aurora-500 to-blue-600 hover:from-aurora-400 hover:to-blue-500 text-space-950 shadow-glow-cyan/20 transition-all flex items-center gap-2"
          >
            <Zap size={14} />
            Onboard AOI
          </Link>
        </div>
      </div>

      {isError && (
        <ErrorCard
          title="Telemetry Feed Disconnected"
          message="Could not reach the FastAPI satellite intelligence server at http://localhost:8000. Ensure the backend process is running."
          onRetry={() => refetch()}
        />
      )}

      {/* Section 1: Geospatial Ingestion Telemetry */}
      <div>
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary mb-3 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-aurora-400" />
          Catalog & Ingestion Fleet
        </h2>
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} lines={1} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="AOIs Monitored"
              value={stats?.aoi_count}
              icon={Map}
              color="cyan"
              sublabel="Active geographic bounds"
            />
            <StatCard
              label="Satellite Scenes"
              value={stats?.scene_count}
              icon={Satellite}
              color="violet"
              sublabel="Copernicus Sentinel-2"
            />
            <StatCard
              label="Indexed Tiles"
              value={stats?.tile_count}
              icon={Grid}
              color="emerald"
              sublabel="224x224 MGRS chips"
            />
            <StatCard
              label="Vector Embeddings"
              value={stats?.vector_count}
              icon={Cpu}
              color="cyan"
              sublabel="ViT-B-32 512-dim vectors"
            />
          </div>
        )}
      </div>

      {/* Section 2: Change Detection Intelligence Metrics */}
      <div>
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary mb-3 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-light" />
          Multi-Temporal Change Surveillance
        </h2>
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} lines={1} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Candidates Scored"
              value={stats?.candidates_scored}
              icon={Radar}
              color="cyan"
              sublabel="Temporal pairs evaluated"
            />
            <StatCard
              label="Candidates Promoted"
              value={stats?.candidates_promoted}
              icon={TrendingUp}
              color="violet"
              sublabel="Signal above calibrated threshold"
            />
            <StatCard
              label="Analyst Confirmed"
              value={stats?.candidates_confirmed}
              icon={CheckCircle2}
              color="emerald"
              glow
              sublabel="Verified ground-truth changes"
            />
            <StatCard
              label="Suppressed (False Positives)"
              value={stats?.candidates_suppressed}
              icon={ShieldAlert}
              color="rose"
              glow
              sublabel="Cloud/snow/quality gated"
            />
          </div>
        )}
      </div>

      {/* Section 3: Engine Architecture & Pipeline Health Panel */}
      <GlassPanel className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Live System State</h2>
            <p className="text-xs text-text-secondary mt-1">Measured from the active catalog and local services</p>
          </div>
          <Activity size={18} className="text-aurora-400" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 font-mono text-xs">
          <div><span className="text-[10px] uppercase text-text-muted block">Clusters</span><span className="text-text-primary font-semibold">{stats?.discovery_clusters ?? '—'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">Accelerating</span><span className="text-text-primary font-semibold">{stats?.accelerating_tiles ?? '—'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">SAR Candidates</span><span className="text-text-primary font-semibold">{stats?.sar_supported_candidates ?? '—'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">SAR Status</span><span className="text-text-primary font-semibold">{stats?.sar_status ?? '—'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">Learner</span><span className="text-text-primary font-semibold">{stats?.learner_status ?? '—'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">LLM</span><span className="text-text-primary font-semibold">{stats?.llm_available && stats?.llm_model_pulled ? 'AVAILABLE' : 'OFFLINE'}</span></div>
          <div><span className="text-[10px] uppercase text-text-muted block">Model</span><span className="text-text-primary font-semibold truncate">{stats?.llm_model ?? '—'}</span></div>
        </div>
      </GlassPanel>

      {/* Section 3: Engine Architecture & Pipeline Health Panel */}
      <GlassPanel className="p-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-2xl bg-white/[0.04] border border-white/[0.08] text-aurora-400">
              <Terminal size={24} />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-text-primary">
                  Satellite Intelligence Engine
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ONLINE
                </span>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed max-w-xl">
                Operating 19-stage offline pipeline: RemoteCLIP ViT-B-32 embeddings,
                MGRS tiling, FAISS L2 vector indexing, calibrated thresholding, and automated
                provenance logging.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 w-full lg:w-auto font-mono text-xs border-t lg:border-t-0 lg:border-l border-white/[0.08] pt-4 lg:pt-0 lg:pl-6">
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Processing Engine</span>
              <span className="text-text-primary font-semibold">
                {stats?.processing_version || 'v0.2-innovations'}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Embedding Dim</span>
              <span className="text-text-primary font-semibold">512-dim (CLIP)</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-text-muted block">Tile Scale</span>
              <span className="text-text-primary font-semibold">224px (10m Res)</span>
            </div>
          </div>
        </div>
      </GlassPanel>
    </div>
  );
};
