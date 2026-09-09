import React from 'react';
import { GlassPanel } from './GlassPanel';
import { AnimatedCounter } from './AnimatedCounter';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  label: string;
  value: number | null | undefined;
  icon: LucideIcon;
  sublabel?: string;
  color?: 'cyan' | 'violet' | 'emerald' | 'rose' | 'amber';
  glow?: boolean;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  sublabel,
  color = 'cyan',
  glow = false,
  className,
}) => {
  const iconColor = {
    cyan: 'text-aurora-400 bg-aurora-500/10 border-aurora-500/20',
    violet: 'text-violet-light bg-purple-500/10 border-purple-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  }[color];

  const glowColorMap = {
    cyan: 'cyan' as const,
    emerald: 'emerald' as const,
    rose: 'rose' as const,
    violet: 'cyan' as const,
    amber: 'none' as const,
  };

  return (
    <GlassPanel
      hoverEffect
      glowColor={glow ? glowColorMap[color] : 'none'}
      className={cn('p-5 flex flex-col justify-between min-h-[128px]', className)}
    >
      <div className="flex items-start justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-text-secondary font-medium">
          {label}
        </span>
        <div className={cn('p-2 rounded-xl border', iconColor)}>
          <Icon size={18} />
        </div>
      </div>
      <div className="mt-4">
        <div className="font-mono text-2xl lg:text-3xl font-bold tracking-tight text-text-primary">
          <AnimatedCounter value={value ?? 0} />
        </div>
        {sublabel && (
          <p className="text-[11px] text-text-muted mt-1 font-mono">{sublabel}</p>
        )}
      </div>
    </GlassPanel>
  );
};
