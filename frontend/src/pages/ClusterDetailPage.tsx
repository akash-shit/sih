import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useClusterMembers } from '@/hooks/useClusters';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TileThumbnail } from '@/components/common/TileThumbnail';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate } from '@/lib/utils';
import { ArrowLeft, Network } from 'lucide-react';
import { motion } from 'framer-motion';

export const ClusterDetailPage: React.FC = () => {
  const { clusterId } = useParams<{ clusterId: string }>();
  const navigate = useNavigate();

  const { data: members, isLoading, isError, refetch } = useClusterMembers(clusterId);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/clusters')}
          className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary hover:text-text-primary border border-white/[0.08] transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl lg:text-2xl font-bold tracking-tight font-mono text-text-primary">
              Cluster #{clusterId} Members
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-violet-500/10 text-violet-light border border-violet-500/20">
              {members?.length || 0} Optical Chips
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5 font-mono">
            Tiles sharing cohesive high-dimensional embedding centroid proximity
          </p>
        </div>
      </div>

      {isError && (
        <ErrorCard
          title="Failed to Load Cluster Members"
          message={`Could not load member tiles belonging to cluster #${clusterId}.`}
          onRetry={() => refetch()}
        />
      )}

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonCard key={i} lines={2} hasThumbnail />
          ))}
        </div>
      ) : !members || members.length === 0 ? (
        <EmptyState
          icon={Network}
          title="No Tiles in this Cluster"
          description="This cluster currently has zero constituent tiles in the catalog."
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {members.map((member, index) => (
            <motion.div
              key={member.tile_id + index}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.02, duration: 0.25 }}
            >
              <GlassPanel
                hoverEffect
                onClick={() => navigate(`/tiles/${member.tile_id}`)}
                className="p-2.5 cursor-pointer group space-y-2"
              >
                <div className="aspect-square rounded-lg overflow-hidden border border-white/[0.08]">
                  <TileThumbnail
                    src={member.thumbnail_url}
                    alt={member.tile_id}
                    aspectRatio="square"
                  />
                </div>
                <div className="font-mono text-xs space-y-0.5">
                  <div className="text-text-primary font-semibold truncate group-hover:text-aurora-300 transition-colors">
                    {member.tile_id}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-text-muted">
                    <span className="capitalize">{member.aoi_id}</span>
                    <span>{formatDate(member.date)}</span>
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
