import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTile, useSimilarTiles } from '@/hooks/useTiles';
import { useStoryline, useTemporalSignature } from '@/hooks/useTemporalSignature';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TileThumbnail } from '@/components/common/TileThumbnail';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatCoord, formatPercent } from '@/lib/utils';
import { ArrowLeft, Compass, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

import { ImageZoomModal } from '@/components/common/ImageZoomModal';
import { TemporalSignatureChart } from '@/components/common/TemporalSignatureChart';
import { MiniBar } from '@/components/common/MiniBar';

export const TileDetailPage: React.FC = () => {
  const { tileId } = useParams<{ tileId: string }>();
  const navigate = useNavigate();
  const [zoomImage, setZoomImage] = useState<string | null>(null);

  const { data: tile, isLoading: tileLoading, isError: tileError } = useTile(tileId);
  const { data: similarTiles, isLoading: similarLoading } = useSimilarTiles(tileId, 12);
  const { data: temporal } = useTemporalSignature(tileId);
  const { data: storyline } = useStoryline(tileId);

  return (
    <div className="space-y-8">
      {/* Back button & header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary hover:text-text-primary border border-white/[0.08] transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl lg:text-2xl font-bold tracking-tight font-mono text-text-primary">
              Tile: {tileId}
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-aurora-500/10 text-aurora-400 border border-aurora-500/20">
              Vector ID #{tile?.vector_id ?? '—'}
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-mono">
            MGRS Optical Footprint & Deep Feature Representation
          </p>
        </div>
      </div>

      {tileError && (
        <ErrorCard title="Tile Not Found" message={`Could not locate tile ${tileId} in catalog.`} />
      )}

      {tileLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SkeletonCard className="lg:col-span-1" hasThumbnail lines={6} />
          <SkeletonCard className="lg:col-span-2" lines={8} />
        </div>
      ) : tile && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Tile Imagery & Location */}
          <GlassPanel className="p-5 space-y-5 lg:col-span-1">
            <div className="w-full aspect-square rounded-lg overflow-hidden border border-white/[0.1]">
              <TileThumbnail
                src={tile.thumbnail_url}
                alt={tile.tile_id}
                aspectRatio="square"
                zoomOnHover
                onOpenZoom={(src) => setZoomImage(src ?? null)}
                showZoomButton
              />
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-text-muted">AOI Domain</span>
                <span className="text-text-primary font-semibold capitalize">{tile.aoi_id}</span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-text-muted">Observation Date</span>
                <span className="text-aurora-300 font-semibold">{formatDate(tile.date)}</span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-text-muted">Sensor Fleet</span>
                <span className="text-text-primary">{tile.sensor || 'SENTINEL2'}</span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-text-muted">Centroid (Lat, Lon)</span>
                <span className="text-text-primary font-medium">
                  {formatCoord(tile.lat)}, {formatCoord(tile.lon)}
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-text-muted">Cluster Group</span>
                <span className="text-violet-light font-semibold">
                  {tile.cluster_id !== null ? `Cluster #${tile.cluster_id}` : 'Unclustered'}
                </span>
              </div>
            </div>
          </GlassPanel>

          {/* Right Column: Multi-Spectral Telemetry & Physical Features */}
          <div className="lg:col-span-2 space-y-6">
            {temporal && <GlassPanel className="p-6"><TemporalSignatureChart series={temporal.series} trend={temporal.trend} /></GlassPanel>}
            {storyline && <GlassPanel className="p-6 space-y-4"><div className="flex items-center justify-between"><h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary">Storyline</h3><span className="px-2 py-0.5 rounded border border-aurora-500/30 bg-aurora-500/10 text-aurora-300 text-[10px] font-mono uppercase">{storyline.stage.replace('_', ' ')}</span></div><div className="grid grid-cols-3 gap-3"><MiniBar label="Short" value={storyline.profile.short} color="cyan" /><MiniBar label="Seasonal" value={storyline.profile.seasonal} color="amber" /><MiniBar label="Long" value={storyline.profile.long} color="emerald" /></div><TemporalSignatureChart values={storyline.velocities} trend={temporal?.trend} className="h-32 w-full" /></GlassPanel>}
            <GlassPanel className="p-6 space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
                <Compass size={14} className="text-aurora-400" />
                Multi-Spectral Band Indices & Radiometric Quality
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    NDVI Mean
                  </span>
                  <span className="text-xl font-mono font-bold text-emerald-400 mt-1 block">
                    {tile.ndvi_mean !== null ? tile.ndvi_mean.toFixed(3) : '—'}
                  </span>
                  <span className="text-[9px] font-mono text-text-muted">Vegetation Index</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    NDWI Mean
                  </span>
                  <span className="text-xl font-mono font-bold text-aurora-400 mt-1 block">
                    {tile.ndwi_mean !== null ? tile.ndwi_mean.toFixed(3) : '—'}
                  </span>
                  <span className="text-[9px] font-mono text-text-muted">Water Index</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    Cloud Cover
                  </span>
                  <span className="text-xl font-mono font-bold text-text-primary mt-1 block">
                    {formatPercent(tile.cloud_fraction, 1)}
                  </span>
                  <span className="text-[9px] font-mono text-text-muted">Mask Fraction</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <span className="text-[10px] font-mono uppercase text-text-muted block">
                    Valid Pixels
                  </span>
                  <span className="text-xl font-mono font-bold text-emerald-300 mt-1 block">
                    {formatPercent(tile.valid_pixel_fraction, 1)}
                  </span>
                  <span className="text-[9px] font-mono text-text-muted">Quality Gate</span>
                </div>
              </div>

              <div className="pt-2 text-xs font-mono text-text-muted space-y-1">
                <div>Scene Ref: <span className="text-text-secondary">{tile.scene_id}</span></div>
                <div>Bounding Box: <span className="text-text-secondary">[{tile.bbox.map(b => b.toFixed(4)).join(', ')}]</span></div>
                <div>Date Provenance: <span className="text-text-secondary">{tile.acquisition_date_source || 'Metadata Tag'}</span></div>
              </div>
            </GlassPanel>

            {/* Nearest Neighbors Semantic Vector Search */}
            <div className="space-y-3">
              <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
                <Cpu size={14} className="text-aurora-400" />
                Nearest Visual Neighbors (FAISS Vector Space)
              </h3>

              {similarLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <SkeletonCard key={i} lines={1} hasThumbnail />
                  ))}
                </div>
              ) : !similarTiles || similarTiles.length === 0 ? (
                <GlassPanel className="p-6 text-center text-xs font-mono text-text-muted">
                  No nearest neighbor embeddings indexed in FAISS for this tile yet.
                </GlassPanel>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {similarTiles.slice(0, 8).map((sim, i) => (
                    <motion.div
                      key={sim.tile_id + i}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.04 }}
                    >
                      <GlassPanel
                        hoverEffect
                        onClick={() => navigate(`/tiles/${sim.tile_id}`)}
                        className="p-2.5 cursor-pointer space-y-2"
                      >
                        <TileThumbnail
                          src={sim.thumbnail_url}
                          alt={sim.tile_id}
                          aspectRatio="square"
                          onOpenZoom={(src) => setZoomImage(src ?? null)}
                          showZoomButton
                        />
                        <div className="flex items-center justify-between text-[11px] font-mono">
                          <span className="text-text-muted truncate">{sim.tile_id}</span>
                          <span className="text-aurora-300 font-semibold">
                            {formatPercent(sim.similarity)}
                          </span>
                        </div>
                      </GlassPanel>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <ImageZoomModal
        src={zoomImage}
        alt="Satellite tile detail"
        open={Boolean(zoomImage)}
        onClose={() => setZoomImage(null)}
      />
    </div>
  );
};
