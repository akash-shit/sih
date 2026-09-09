import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAOIs } from '@/hooks/useAOIs';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TileThumbnail } from '@/components/common/TileThumbnail';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate, formatCoord } from '@/lib/utils';
import { Map, Layers, Grid, Calendar, Clock, Plus, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

export const AOIPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: aois, isLoading, isError, refetch } = useAOIs();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Areas of Interest (AOIs)
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Geographic catalog partitions with multi-temporal scene stacks
          </p>
        </div>
        <button
          onClick={() => navigate('/onboard')}
          className="px-4 py-2 rounded-xl text-xs font-mono font-medium bg-gradient-to-r from-aurora-500 to-blue-600 hover:from-aurora-400 hover:to-blue-500 text-space-950 shadow-glow-cyan/20 flex items-center gap-2 self-start"
        >
          <Plus size={14} />
          Onboard New AOI
        </button>
      </div>

      {isError && (
        <ErrorCard
          title="Failed to Load AOIs"
          message="Could not retrieve the registered Areas of Interest from the catalog database."
          onRetry={() => refetch()}
        />
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} hasThumbnail lines={4} />
          ))}
        </div>
      ) : !aois || aois.length === 0 ? (
        <EmptyState
          icon={Map}
          title="No AOIs Onboarded Yet"
          description="Initialize your satellite catalog by onboarding a Copernicus Sentinel-2 export archive."
          action={{
            label: 'Onboard First AOI',
            onClick: () => navigate('/onboard'),
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {aois.map((aoi, index) => (
            <motion.div
              key={aoi.aoi_id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08, duration: 0.4 }}
            >
              <GlassPanel
                hoverEffect
                onClick={() => navigate(`/aois/${aoi.aoi_id}`)}
                className="cursor-pointer group flex flex-col h-full overflow-hidden"
              >
                {/* Mosaic Preview */}
                <div className="relative h-48 w-full overflow-hidden">
                  <TileThumbnail
                    src={aoi.mosaic_thumbnail_url}
                    alt={aoi.name}
                    aspectRatio="wide"
                    className="w-full h-full rounded-none border-none"
                  />
                  <div className="absolute top-3 right-3 px-2 py-1 rounded-md bg-space-950/80 backdrop-blur-md border border-white/[0.1] text-[10px] font-mono text-aurora-300 flex items-center gap-1.5 opacity-90 group-hover:opacity-100 group-hover:border-aurora-500/40 transition-all">
                    <span>Inspect</span>
                    <ArrowUpRight size={12} />
                  </div>
                </div>

                {/* Body Details */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div>
                    <h3 className="text-lg font-bold text-text-primary capitalize tracking-tight group-hover:text-aurora-300 transition-colors">
                      {aoi.name}
                    </h3>
                    <p className="text-[11px] font-mono text-text-muted mt-1 truncate">
                      BBOX: [{formatCoord(aoi.bbox[0])}, {formatCoord(aoi.bbox[1])}] to [
                      {formatCoord(aoi.bbox[2])}, {formatCoord(aoi.bbox[3])}]
                    </p>
                  </div>

                  {/* Badges & Metrics */}
                  <div className="grid grid-cols-2 gap-2 py-2 border-y border-white/[0.06]">
                    <div className="flex items-center gap-2 text-xs font-mono text-text-secondary">
                      <Layers size={14} className="text-violet-light" />
                      <span>{aoi.scene_count} scenes</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono text-text-secondary">
                      <Grid size={14} className="text-emerald-400" />
                      <span>{aoi.tile_count} chips</span>
                    </div>
                  </div>

                  {/* Temporal Extent & Activity */}
                  <div className="space-y-1 text-[11px] font-mono text-text-muted">
                    <div className="flex items-center gap-1.5">
                      <Calendar size={12} className="text-text-secondary shrink-0" />
                      <span className="truncate">
                        {formatDate(aoi.start_date)} → {formatDate(aoi.end_date)}
                      </span>
                    </div>
                    {aoi.last_activity && (
                      <div className="flex items-center gap-1.5">
                        <Clock size={12} className="text-text-secondary shrink-0" />
                        <span className="truncate">
                          Updated {formatDate(aoi.last_activity)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </GlassPanel>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
