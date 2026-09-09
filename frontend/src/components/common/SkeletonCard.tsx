import React from 'react';
import { cn } from '@/lib/utils';
import { GlassPanel } from './GlassPanel';

interface SkeletonCardProps {
  className?: string;
  lines?: number;
  hasThumbnail?: boolean;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  className,
  lines = 3,
  hasThumbnail = false,
}) => {
  return (
    <GlassPanel className={cn('p-5 space-y-4', className)}>
      {hasThumbnail && (
        <div className="relative h-44 w-full rounded-lg bg-white/[0.04] overflow-hidden">
          <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
        </div>
      )}
      <div className="space-y-2.5">
        <div className="relative h-5 w-2/3 rounded bg-white/[0.06] overflow-hidden">
          <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
        </div>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="relative h-3 rounded bg-white/[0.03] overflow-hidden"
            style={{ width: `${85 - i * 15}%` }}
          >
            <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
          </div>
        ))}
      </div>
    </GlassPanel>
  );
};
