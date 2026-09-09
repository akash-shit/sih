import React from 'react';
import { Cpu } from 'lucide-react';
import { motion } from 'framer-motion';
import { GlassPanel } from './GlassPanel';
import { TileThumbnail } from './TileThumbnail';
import { SkeletonCard } from './SkeletonCard';
import { useSimilarTilesByVector } from '@/hooks/useTiles';
import { formatPercent } from '@/lib/utils';

interface SimilarTileGridProps {
  vectorId: number | null | undefined;
  label: string;
  onNavigate: (tileId: string) => void;
  onOpenZoom: (src: string | null | undefined) => void;
}

export const SimilarTileGrid: React.FC<SimilarTileGridProps> = ({
  vectorId,
  label,
  onNavigate,
  onOpenZoom,
}) => {
  const { data: similarTiles, isLoading } = useSimilarTilesByVector(vectorId, 12);

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
        <Cpu size={14} className="text-aurora-400" />
        {label}
      </h3>
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, index) => <SkeletonCard key={index} lines={1} hasThumbnail />)}
        </div>
      ) : !similarTiles || similarTiles.length === 0 ? (
        <GlassPanel className="p-6 text-center text-xs font-mono text-text-muted">
          No nearest neighbor embeddings indexed for this tile yet.
        </GlassPanel>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {similarTiles.slice(0, 8).map((tile, index) => (
            <motion.div
              key={`${tile.tile_id}-${tile.vector_id ?? index}`}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.04 }}
            >
              <GlassPanel
                hoverEffect
                onClick={() => onNavigate(tile.tile_id)}
                className="p-2.5 cursor-pointer space-y-2"
              >
                <TileThumbnail
                  src={tile.thumbnail_url}
                  alt={tile.tile_id}
                  aspectRatio="square"
                  onOpenZoom={onOpenZoom}
                  showZoomButton
                />
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-text-muted truncate">{tile.tile_id}</span>
                  <span className="text-aurora-300 font-semibold">{formatPercent(tile.similarity)}</span>
                </div>
              </GlassPanel>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
