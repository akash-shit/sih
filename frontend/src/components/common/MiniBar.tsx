import React from 'react';
import { cn, formatPercent } from '@/lib/utils';

interface MiniBarProps {
  label: string;
  value: number | null | undefined;
  color?: 'cyan' | 'violet' | 'gradient' | 'emerald' | 'amber';
  className?: string;
  showValue?: boolean;
}

export const MiniBar: React.FC<MiniBarProps> = ({
  label,
  value,
  color = 'cyan',
  className,
  showValue = true,
}) => {
  const percentage = Math.max(0, Math.min(100, (value ?? 0) * 100));

  const colorStyles = {
    cyan: 'bg-aurora-400',
    violet: 'bg-violet-400',
    gradient: 'bg-gradient-to-r from-aurora-400 via-violet-400 to-rose-400',
    emerald: 'bg-emerald-400',
    amber: 'bg-amber-400',
  }[color];

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-text-secondary font-mono text-[10px] tracking-wide uppercase">{label}</span>
        {showValue && (
          <span className="font-mono text-text-primary text-[10px] font-medium">
            {formatPercent(value, 1)}
          </span>
        )}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
        <div
          className={cn('h-full rounded-full transition-all duration-500 ease-out', colorStyles)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
