import React from 'react';
import { cn, formatPercent } from '@/lib/utils';

interface ScoreGaugeProps {
  score: number | null | undefined;
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
  color?: 'cyan' | 'emerald' | 'violet' | 'amber';
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 48,
  strokeWidth = 4,
  label,
  className,
  color = 'cyan',
}) => {
  const normalizedScore = Math.max(0, Math.min(1, score ?? 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - normalizedScore * circumference;

  const colorMap = {
    cyan: 'text-aurora-400 stroke-aurora-400',
    emerald: 'text-emerald-400 stroke-emerald-400',
    violet: 'text-violet-light stroke-violet-light',
    amber: 'text-amber-400 stroke-amber-400',
  }[color];

  return (
    <div className={cn('relative inline-flex flex-col items-center justify-center', className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="stroke-white/[0.08]"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className={cn('transition-all duration-700 ease-out', colorMap)}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono text-[11px] font-semibold tracking-tighter text-text-primary">
          {formatPercent(score)}
        </span>
      </div>
      {label && <span className="mt-1 text-[10px] text-text-muted uppercase tracking-wider">{label}</span>}
    </div>
  );
};
