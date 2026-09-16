import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useStartOnboard, useOnboardJob } from '@/hooks/useOnboard';
import { GlassPanel } from '@/components/common/GlassPanel';
import { formatDate } from '@/lib/utils';
import { toast } from 'sonner';
import {
  UploadCloud,
  AlertTriangle,
  ArrowRight,
  Activity,
  FileCheck,
} from 'lucide-react';
import { motion } from 'framer-motion';

export const OnboardPage: React.FC = () => {
  const [aoiName, setAoiName] = useState('');
  const [sourceFolder, setSourceFolder] = useState('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [priorityTier, setPriorityTier] = useState('medium');
  const [priorityGeojson, setPriorityGeojson] = useState('');

  const startOnboard = useStartOnboard();
  const { data: job } = useOnboardJob(activeJobId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aoiName.trim() || !sourceFolder.trim()) return;

    startOnboard.mutate(
      {
        name: aoiName.trim().toLowerCase(),
        source_folder: sourceFolder.trim(),
        priority_tier: priorityTier,
        priority_geojson: priorityGeojson || undefined,
      },
      {
        onSuccess: (data) => {
          setActiveJobId(data.job_id);
          toast.success(`Onboarding initiated for ${aoiName}!`, {
            description: `Job ID: ${data.job_id}`,
          });
        },
        onError: (err) => {
          toast.error('Failed to initiate onboarding job', {
            description: err.message,
          });
        },
      }
    );
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <label className="block text-xs font-mono uppercase text-text-muted mb-2">Priority tier</label>
        <select value={priorityTier} onChange={(e) => setPriorityTier(e.target.value)} className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-sm text-text-primary">
          <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
        </select>
      </div>
      <div>
        <label className="block text-xs font-mono uppercase text-text-muted mb-2">Priority GeoJSON (optional)</label>
        <textarea value={priorityGeojson} onChange={(e) => setPriorityGeojson(e.target.value)} rows={3} className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-sm font-mono text-text-primary" />
      </div>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">
          Onboard New Area of Interest (AOI)
        </h1>
        <p className="text-xs text-text-secondary mt-1 font-mono">
          Batch validate and ingest Copernicus Sentinel-2 zip archives or pre-processed GeoTIFF scenes
        </p>
      </div>

      {/* Onboarding Form */}
      <GlassPanel className="p-6 md:p-8 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-mono uppercase text-text-muted mb-2">
              AOI Name / Ground Slug
            </label>
            <input
              type="text"
              value={aoiName}
              onChange={(e) => setAoiName(e.target.value)}
              placeholder="e.g. dholera or gandhinagar"
              required
              className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400 focus:ring-1 focus:ring-aurora-400 transition-all"
            />
            <p className="text-[11px] font-mono text-text-muted mt-1">
              Must be a unique identifier used to catalog scenes, tiles, and bounding boxes.
            </p>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-text-muted mb-2">
              Server Source Folder Path
            </label>
            <input
              type="text"
              value={sourceFolder}
              onChange={(e) => setSourceFolder(e.target.value)}
              placeholder="e.g. /data/raw/dholera_zips or C:/path/to/sentinel_exports"
              required
              className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400 focus:ring-1 focus:ring-aurora-400 transition-all"
            />
            <p className="text-[11px] font-mono text-text-muted mt-1">
              Absolute filesystem path on backend host containing Copernicus .zip files or .tif scenes.
            </p>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={startOnboard.isPending || (job && (job.status === 'running' || job.status === 'queued'))}
              className="w-full sm:w-auto px-6 py-3 rounded-xl font-mono text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-aurora-500 to-blue-600 hover:from-aurora-400 hover:to-blue-500 disabled:opacity-40 text-space-950 shadow-glow-cyan/20 transition-all flex items-center justify-center gap-2"
            >
              <UploadCloud size={16} />
              {startOnboard.isPending ? 'Validating Batch…' : 'Start Onboarding Pipeline'}
            </button>
          </div>
        </form>
      </GlassPanel>

      {/* Live Job Execution Progress Panel */}
      {job && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <GlassPanel className="p-6 md:p-8 space-y-6">
            {/* Header & Status */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-mono text-text-primary">
                    Execution Job #{job.job_id.slice(0, 8)}
                  </h3>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider ${
                      job.status === 'done'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : job.status === 'failed'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : 'bg-aurora-500/10 text-aurora-300 border border-aurora-500/20 animate-pulse'
                    }`}
                  >
                    {job.status}
                  </span>
                </div>
                <p className="text-xs font-mono text-text-muted mt-0.5">
                  Target AOI: <span className="text-text-primary font-semibold capitalize">{job.aoi_id}</span>
                </p>
              </div>

              {job.status === 'done' && (
                <Link
                  to={`/aois/${job.aoi_id}`}
                  className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 flex items-center gap-2 transition-colors self-start sm:self-auto"
                >
                  <FileCheck size={14} />
                  View Cataloged AOI
                  <ArrowRight size={12} />
                </Link>
              )}
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-text-secondary flex items-center gap-2">
                  <Activity size={14} className={job.status === 'running' ? 'text-aurora-400 animate-spin' : 'text-text-muted'} />
                  {job.message || (job.status === 'done' ? 'Onboarding successfully completed' : 'Processing scenes…')}
                </span>
                <span className="font-bold text-text-primary">{job.progress}%</span>
              </div>
              <div className="h-2 w-full bg-white/[0.08] rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full transition-all duration-500 ${
                    job.status === 'done'
                      ? 'bg-emerald-400'
                      : job.status === 'failed'
                      ? 'bg-rose-400'
                      : 'bg-gradient-to-r from-aurora-500 to-blue-500'
                  }`}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>

            {/* Telemetry Summary Counters */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Scenes Discovered
                </span>
                <span className="text-lg font-mono font-bold text-text-primary mt-1 block">
                  {job.scenes_found ?? '—'}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Scenes Ingested
                </span>
                <span className="text-lg font-mono font-bold text-emerald-400 mt-1 block">
                  {job.scenes_ingested ?? '—'}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Failed Scenes
                </span>
                <span className="text-lg font-mono font-bold text-rose-400 mt-1 block">
                  {job.scenes_failed ?? 0}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <span className="text-[10px] font-mono uppercase text-text-muted block">
                  Tiles Indexed
                </span>
                <span className="text-lg font-mono font-bold text-aurora-400 mt-1 block">
                  {job.tiles_added ?? '—'}
                </span>
              </div>
            </div>

            {/* Warnings list if any */}
            {job.warnings && job.warnings.length > 0 && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-1 text-xs font-mono text-amber-300">
                <div className="flex items-center gap-2 font-bold mb-1">
                  <AlertTriangle size={14} className="text-amber-400" />
                  Validation Warnings:
                </div>
                {job.warnings.map((warn, i) => (
                  <div key={i} className="text-[11px] leading-relaxed">
                    • {warn}
                  </div>
                ))}
              </div>
            )}

            {/* Per-Scene Results Table */}
            {job.scenes && job.scenes.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-text-secondary">
                  Scene Batch Outcome ({job.scenes.length} files)
                </h4>
                <div className="max-h-60 overflow-y-auto rounded-xl border border-white/[0.06]">
                  <table className="w-full text-left font-mono text-xs">
                    <thead className="bg-space-950/60 sticky top-0 border-b border-white/[0.06] text-text-muted text-[10px] uppercase">
                      <tr>
                        <th className="py-2.5 px-3">Scene Identifier</th>
                        <th className="py-2.5 px-3">Acquisition Date</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Message</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {job.scenes.map((scene, i) => (
                        <tr key={i} className="hover:bg-white/[0.02]">
                          <td className="py-2.5 px-3 text-text-primary truncate max-w-[200px]">
                            {scene.scene_id}
                          </td>
                          <td className="py-2.5 px-3 text-text-secondary">
                            {formatDate(scene.date)}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] uppercase ${
                                scene.status === 'ok' || scene.status === 'ingested'
                                  ? 'text-emerald-400 bg-emerald-500/10'
                                  : 'text-rose-400 bg-rose-500/10'
                              }`}
                            >
                              {scene.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-text-muted text-[11px] truncate max-w-[220px]">
                            {scene.message || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </GlassPanel>
        </motion.div>
      )}
    </div>
  );
};
