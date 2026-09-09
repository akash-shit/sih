import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAOITimeline, useMosaic } from '@/hooks/useAOIs';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TileThumbnail } from '@/components/common/TileThumbnail';
import { ImageZoomModal } from '@/components/common/ImageZoomModal';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatPercent } from '@/lib/utils';
import {
  ArrowLeft,
  Layers,
  Cloud,
  AlertCircle,
  Crosshair,
  Maximize2,
  Sparkles,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import { motion } from 'framer-motion';

export const AOIDetailPage: React.FC = () => {
  const { aoiId } = useParams<{ aoiId: string }>();
  const navigate = useNavigate();

  const { data: timeline, isLoading: timelineLoading, isError: timelineError } = useAOITimeline(aoiId);

  // Extract unique months from timeline
  const months = React.useMemo(() => {
    if (!timeline) return [];
    const set = new Set<string>();
    timeline.forEach((item) => {
      if (item.date) {
        set.add(item.date.slice(0, 7)); // YYYY-MM
      }
    });
    return Array.from(set).sort().reverse();
  }, [timeline]);

  const [selectedMonth, setSelectedMonth] = useState<string>('');

  useEffect(() => {
    if (months.length > 0 && !selectedMonth) {
      setSelectedMonth(months[0]);
    }
  }, [months, selectedMonth]);

  const {
    data: mosaic,
    isLoading: mosaicLoading,
    isError: mosaicError,
  } = useMosaic(aoiId, selectedMonth);

  const [hoveredTile, setHoveredTile] = useState<string | null>(null);
  const [zoomImage, setZoomImage] = useState<string | null>(null);
  const [mosaicZoom, setMosaicZoom] = useState(1);

  useEffect(() => {
    setMosaicZoom(1);
  }, [selectedMonth, mosaic?.image_url]);

  return (
    <div className="space-y-8">
      {/* Header with Navigation Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/aois')}
            className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary hover:text-text-primary border border-white/[0.08] transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-text-primary capitalize">
                {aoiId}
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-aurora-500/10 text-aurora-400 border border-aurora-500/20">
                Sentinel-2 L2A
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-0.5 font-mono">
              Multi-Temporal Timeline & High-Resolution Tile Matrix
            </p>
          </div>
        </div>

        {/* Month Selector */}
        {months.length > 0 && (
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-text-muted">Observation Month:</span>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-space-850 border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-text-primary font-mono focus:outline-none focus:border-aurora-400"
            >
              {months.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Top Split View: Interactive Mosaic Frame on Left, Details/Stats on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Mosaic Grid Viewer */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
              <Crosshair size={14} className="text-aurora-400" />
              Composite Mosaic & Candidate Vector Grid
            </h2>
            {hoveredTile && (
              <span className="font-mono text-[11px] text-aurora-300">
                Focused Tile: {hoveredTile}
              </span>
            )}
          </div>

          <GlassPanel className="p-2 sm:p-4 bg-space-950/80">
            {mosaicLoading ? (
              <div className="h-[480px] flex items-center justify-center">
                <div className="space-y-3 text-center">
                  <div className="w-8 h-8 border-2 border-aurora-400 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-xs font-mono text-text-muted">
                    Stitching multi-tile mosaic for {selectedMonth}…
                  </p>
                </div>
              </div>
            ) : mosaicError || !mosaic ? (
              <div className="h-[480px] flex items-center justify-center p-6">
                <div className="text-center space-y-2 max-w-sm">
                  <AlertCircle size={28} className="text-amber-400 mx-auto" />
                  <h4 className="text-sm font-semibold text-text-primary">
                    No Composite For Selected Date
                  </h4>
                  <p className="text-xs text-text-secondary">
                    Tiles for month {selectedMonth} are either uncalibrated or lack cloud-free optical coverage.
                  </p>
                </div>
              </div>
            ) : (
              <div className="relative w-full aspect-square max-h-[600px] mx-auto rounded-lg overflow-hidden border border-white/[0.1] select-none bg-black">
                <div
                  className="absolute inset-0 origin-center transition-transform duration-200"
                  style={{ transform: `scale(${mosaicZoom})` }}
                >
                  <img
                    src={mosaic.image_url}
                    alt={`Mosaic ${mosaic.aoi_id} ${mosaic.date}`}
                    onClick={() => setZoomImage(mosaic.image_url)}
                    className="w-full h-full object-contain cursor-zoom-in"
                  />

                  {/* SVG/Div Overlay Grid of 224x224 Tiles */}
                  <div className="absolute inset-0">
                    {mosaic.tiles.map((tile) => {
                      const leftPct = (tile.x / mosaic.width) * 100;
                      const topPct = (tile.y / mosaic.height) * 100;
                      const widthPct = (tile.width / mosaic.width) * 100;
                      const heightPct = (tile.height / mosaic.height) * 100;
                      const isHovered = hoveredTile === tile.tile_id;

                      return (
                        <div
                          key={tile.tile_id}
                          onClick={() => navigate(`/tiles/${tile.tile_id}`)}
                          onMouseEnter={() => setHoveredTile(tile.tile_id)}
                          onMouseLeave={() => setHoveredTile(null)}
                          style={{ left: `${leftPct}%`, top: `${topPct}%`, width: `${widthPct}%`, height: `${heightPct}%` }}
                          className={`absolute border transition-all cursor-pointer group flex items-start justify-end p-1 ${
                            tile.has_change_candidate
                              ? 'border-aurora-400 bg-aurora-500/15 shadow-[inset_0_0_12px_rgba(0,212,255,0.4)] animate-pulse'
                              : 'border-white/[0.1] hover:border-white/50 hover:bg-white/[0.08]'
                          } ${isHovered ? 'z-20 border-white bg-white/20' : 'z-10'}`}
                          title={`Tile ID: ${tile.tile_id}${tile.has_change_candidate ? ' (Candidate Change Detected!)' : ''}`}
                        >
                          {tile.has_change_candidate && <span className="w-2 h-2 rounded-full bg-rose-500 shadow-glow-rose" />}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setZoomImage(mosaic.image_url)}
                  className="absolute right-3 top-3 z-20 inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-space-950/75 px-2.5 py-1.5 text-[10px] font-mono text-text-secondary backdrop-blur-md hover:text-text-primary"
                >
                  <Maximize2 size={12} />
                  Zoom
                </button>
                <div className="absolute bottom-3 left-3 z-20 flex items-center gap-1 rounded-lg border border-white/[0.12] bg-space-950/80 p-1 backdrop-blur-md">
                  <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => setMosaicZoom((value) => Math.max(1, value - 0.25))} className="compare-tool"><ZoomOut size={12} /></button>
                  <button type="button" onClick={() => setMosaicZoom(1)} className="compare-tool">Fit</button>
                  <button type="button" aria-label="Reset zoom" title="Reset zoom" onClick={() => setMosaicZoom(1)} className="compare-tool"><RotateCcw size={12} /></button>
                  <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => setMosaicZoom((value) => Math.min(2.5, value + 0.25))} className="compare-tool"><ZoomIn size={12} /></button>
                </div>
              </div>
            )}
          </GlassPanel>
        </div>

      <ImageZoomModal
        src={zoomImage ?? undefined}
        alt="AOI mosaic detail"
        open={Boolean(zoomImage)}
        onClose={() => setZoomImage(null)}
      />

        {/* Side Panel: Selected Tile / Quick AOI Telemetry */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
            <Maximize2 size={14} className="text-violet-light" />
            Observation Intelligence
          </h2>

          <GlassPanel className="p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-mono text-text-secondary">AOI Identifier</span>
              <span className="text-xs font-mono text-text-primary font-semibold capitalize">
                {aoiId}
              </span>
            </div>

            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-mono text-text-secondary">Target Month</span>
              <span className="text-xs font-mono text-aurora-300 font-semibold">
                {selectedMonth || '—'}
              </span>
            </div>

            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-mono text-text-secondary">Active Tiles in Mosaic</span>
              <span className="text-xs font-mono text-text-primary font-semibold">
                {mosaic?.tiles.length || 0} chips
              </span>
            </div>

            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-mono text-text-secondary">Detected Changes</span>
              <span className="text-xs font-mono text-aurora-400 font-semibold flex items-center gap-1.5">
                <Sparkles size={12} />
                {mosaic?.tiles.filter((t) => t.has_change_candidate).length || 0} anomalies
              </span>
            </div>

            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] text-[11px] text-text-secondary space-y-1">
              <p className="font-semibold text-text-primary font-mono flex items-center gap-1.5">
                <Crosshair size={12} className="text-aurora-400" />
                Interactive Grid Guide:
              </p>
              <p>
                Click any tile rectangle above to open its deep spectral signature, NDVI history, and similar vector neighbors.
              </p>
            </div>
          </GlassPanel>
        </div>
      </div>

      {/* Bottom Section: Multi-Temporal Scene Timeline */}
      <div className="space-y-4">
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
          <Layers size={14} className="text-aurora-400" />
          Scene Ingestion & Provenance Timeline ({timeline?.length || 0} Passes)
        </h2>

        {timelineLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} lines={2} />
            ))}
          </div>
        ) : timelineError ? (
          <ErrorCard title="Timeline Ingestion Error" message="Could not load scene acquisition history." />
        ) : !timeline || timeline.length === 0 ? (
          <GlassPanel className="p-8 text-center text-text-muted text-xs font-mono">
            No satellite acquisition scenes available for this AOI.
          </GlassPanel>
        ) : (
          <div className="space-y-3">
            {timeline.map((scene, index) => {
              const cloud = scene.cloud_fraction ?? 0;
              const cloudColor =
                cloud < 0.15
                  ? 'bg-emerald-400'
                  : cloud < 0.3
                  ? 'bg-amber-400'
                  : 'bg-rose-400';

              return (
                <motion.div
                  key={scene.scene_id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.04, duration: 0.3 }}
                >
                  <GlassPanel
                    hoverEffect
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 shrink-0 rounded-lg overflow-hidden border border-white/[0.08]">
                        <TileThumbnail
                          src={scene.thumbnail_url}
                          alt={scene.scene_id}
                          aspectRatio="square"
                        />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-sm font-semibold text-text-primary">
                            {formatDate(scene.date)}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/[0.05] text-text-secondary border border-white/[0.08]">
                            {scene.sensor || 'SENTINEL2'}
                          </span>
                          {scene.acquisition_date_source && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-violet-light border border-purple-500/20">
                              {scene.acquisition_date_source}
                            </span>
                          )}
                        </div>
                        <p className="font-mono text-xs text-text-muted">{scene.scene_id}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 justify-between md:justify-end border-t md:border-t-0 border-white/[0.06] pt-3 md:pt-0">
                      {/* Cloud Cover Telemetry */}
                      <div className="space-y-1 min-w-[130px]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-text-secondary">
                          <span className="flex items-center gap-1">
                            <Cloud size={12} />
                            Cloud:
                          </span>
                          <span className="text-text-primary font-semibold">
                            {formatPercent(scene.cloud_fraction, 1)}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-white/[0.08] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${cloudColor}`}
                            style={{ width: `${Math.min(100, cloud * 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Tile Count */}
                      <div className="text-right font-mono">
                        <span className="text-xs text-text-muted block text-[10px] uppercase">
                          Chips Extracted
                        </span>
                        <span className="text-sm font-semibold text-text-primary">
                          {scene.tile_count}
                        </span>
                      </div>
                    </div>
                  </GlassPanel>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
