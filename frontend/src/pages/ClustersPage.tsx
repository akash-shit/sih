import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useClusters } from '@/hooks/useClusters';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TileThumbnail } from '@/components/common/TileThumbnail';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate } from '@/lib/utils';
import { Network, Tag, Calendar, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

export const ClustersPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: clusters, isLoading, isError, refetch } = useClusters();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Unsupervised Discovery Clusters
          </h1>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Semantic partitions discovered across FAISS high-dimensional vector space
          </p>
        </div>
      </div>

      {isError && (
        <ErrorCard
          title="Cluster Retrieval Failure"
          message="Could not load unsupervised semantic clusters from discovery stage."
          onRetry={() => refetch()}
        />
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} hasThumbnail lines={4} />
          ))}
        </div>
      ) : !clusters || clusters.length === 0 ? (
        <EmptyState
          icon={Network}
          title="No Clusters Discovered Yet"
          description="Clustering runs across indexed tile embeddings to group visually and semantically similar landscapes automatically."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clusters.map((cluster, index) => (
            <motion.div
              key={cluster.cluster_id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
            >
              <GlassPanel
                hoverEffect
                onClick={() => navigate(`/clusters/${cluster.cluster_id}`)}
                className="cursor-pointer group flex flex-col justify-between h-full p-5 space-y-4"
              >
                {/* Centroid Thumbnail */}
                <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-white/[0.08]">
                  <TileThumbnail
                    src={cluster.representative_thumbnail_url}
                    alt={`Cluster ${cluster.cluster_id}`}
                    aspectRatio="video"
                  />
                  <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-space-950/80 backdrop-blur-md border border-white/[0.1] text-[10px] font-mono text-aurora-300 flex items-center gap-1 group-hover:border-aurora-500/40 transition-colors">
                    <span>Inspect</span>
                    <ArrowUpRight size={11} />
                  </div>
                </div>

                {/* Header info */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-mono text-base font-bold text-text-primary group-hover:text-aurora-300 transition-colors">
                      Cluster #{cluster.cluster_id}
                    </h3>
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-violet-500/10 text-violet-light border border-violet-500/20">
                      {cluster.member_count} members
                    </span>
                  </div>

                  <p className="text-xs font-mono text-text-muted flex items-center gap-1.5">
                    <Tag size={12} />
                    {cluster.label || 'Unlabeled Cluster'}
                  </p>
                </div>

                {/* AOI membership tags */}
                <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-white/[0.06]">
                  <span className="text-[10px] font-mono text-text-muted">AOIs:</span>
                  {cluster.aoi_ids.map((aoi) => (
                    <span
                      key={aoi}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/[0.04] text-text-secondary border border-white/[0.08] capitalize"
                    >
                      {aoi}
                    </span>
                  ))}
                </div>

                {/* Date range */}
                <div className="text-[11px] font-mono text-text-muted flex items-center gap-1.5 pt-1">
                  <Calendar size={12} className="text-text-secondary shrink-0" />
                  <span className="truncate">
                    {formatDate(cluster.start_date)} → {formatDate(cluster.end_date)}
                  </span>
                </div>
              </GlassPanel>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
