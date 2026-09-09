import React from 'react';
import { cn } from '@/lib/utils';
import type { ChangeStatus } from '@/types/api';

interface StatusBadgeProps {
  status: ChangeStatus | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className,
  size = 'md',
}) => {
  const normalized = (status || '').toUpperCase() as ChangeStatus;

  const styleMap: Record<ChangeStatus, { bg: string; text: string; border: string; dot: string }> = {
    OPEN: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      dot: 'bg-amber-400',
    },
    CONFIRMED: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      dot: 'bg-emerald-400',
    },
    REJECTED: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      dot: 'bg-rose-400',
    },
    SUPPRESSED: {
      bg: 'bg-zinc-500/10',
      text: 'text-zinc-400',
      border: 'border-zinc-500/20',
      dot: 'bg-zinc-400',
    },
  };

  const style = styleMap[normalized] || styleMap.SUPPRESSED;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-mono font-medium rounded-full border tracking-wide uppercase',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs',
        style.bg,
        style.text,
        style.border,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', style.dot)} />
      {normalized}
    </span>
  );
};
