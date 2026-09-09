import React from 'react';
import { GlassPanel } from './GlassPanel';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorCardProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorCard: React.FC<ErrorCardProps> = ({
  title = 'Telemetry Error',
  message = 'Failed to load remote satellite telemetry. Please check the backend connection.',
  onRetry,
  className,
}) => {
  return (
    <GlassPanel
      glowColor="rose"
      className={`p-6 border-rose-500/20 bg-rose-950/10 ${className || ''}`}
    >
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 shrink-0">
          <AlertTriangle size={20} />
        </div>
        <div className="space-y-1 flex-1">
          <h4 className="text-sm font-semibold text-rose-200">{title}</h4>
          <p className="text-xs text-rose-300/70 leading-relaxed">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/20 text-rose-200 hover:bg-rose-500/30 border border-rose-500/30 transition-colors"
            >
              <RefreshCw size={12} />
              Retry Request
            </button>
          )}
        </div>
      </div>
    </GlassPanel>
  );
};
