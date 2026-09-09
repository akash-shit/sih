import React from 'react';
import { cn } from '@/lib/utils';
import { useStats } from '@/hooks/useStats';

interface ApiStatusIndicatorProps {
  className?: string;
}

export const ApiStatusIndicator: React.FC<ApiStatusIndicatorProps> = ({ className }) => {
  const { data, isLoading, isError } = useStats();

  let statusText = 'Pipeline Online';
  let dotColor = 'bg-emerald-400';
  let pingColor = 'bg-emerald-400';

  if (isLoading) {
    statusText = 'Checking Telemetry…';
    dotColor = 'bg-amber-400';
    pingColor = 'bg-amber-400';
  } else if (isError) {
    statusText = 'Telemetry Offline';
    dotColor = 'bg-rose-400';
    pingColor = 'bg-rose-400';
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] backdrop-blur-md',
        className
      )}
      title={data?.processing_version ? `Engine: ${data.processing_version}` : undefined}
    >
      <span className="relative flex h-2 w-2">
        {!isError && (
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              pingColor
            )}
          />
        )}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', dotColor)} />
      </span>
      <span className="text-xs font-mono text-text-secondary tracking-tight">
        {statusText}
      </span>
    </div>
  );
};
