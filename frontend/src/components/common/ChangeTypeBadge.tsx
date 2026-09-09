import React from 'react';
import { cn } from '@/lib/utils';
import { Building, TreePine, Waves, Milestone, CircleHelp, CircleDashed } from 'lucide-react';
import type { ChangeType } from '@/types/api';

interface ChangeTypeBadgeProps {
  type: ChangeType | null | undefined;
  className?: string;
  size?: 'sm' | 'md';
}

export const ChangeTypeBadge: React.FC<ChangeTypeBadgeProps> = ({
  type,
  className,
  size = 'md',
}) => {
  const iconSize = size === 'sm' ? 12 : 14;

  switch (type) {
    case 'construction':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-cyan-500/10 text-aurora-400 border-aurora-500/20',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <Building size={iconSize} className="text-aurora-400" />
          Construction
        </span>
      );
    case 'vegetation_clearance':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-amber-500/10 text-amber-400 border-amber-500/20',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <TreePine size={iconSize} className="text-amber-400" />
          Vegetation Clearance
        </span>
      );
    case 'water_extent_change':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-blue-500/10 text-blue-400 border-blue-500/20',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <Waves size={iconSize} className="text-blue-400" />
          Water Change
        </span>
      );
    case 'road_development':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-purple-500/10 text-violet-300 border-purple-500/20',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <Milestone size={iconSize} className="text-violet-light" />
          Road Development
        </span>
      );
    case 'no_clear_category':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <CircleHelp size={iconSize} className="text-zinc-400" />
          Unclassified
        </span>
      );
    default:
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md font-medium border bg-zinc-800/40 text-text-muted border-white/[0.08]',
            size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs',
            className
          )}
        >
          <CircleDashed size={iconSize} className="text-text-muted" />
          Unanalyzed
        </span>
      );
  }
};
