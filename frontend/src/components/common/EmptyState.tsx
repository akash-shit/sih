import React from 'react';
import { GlassPanel } from './GlassPanel';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <GlassPanel className={`p-12 text-center flex flex-col items-center justify-center max-w-lg mx-auto ${className || ''}`}>
      <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mb-4 text-aurora-400">
        <Icon size={28} />
      </div>
      <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
      <p className="text-sm text-text-secondary mb-6 max-w-sm">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 rounded-xl text-sm font-medium bg-aurora-500 text-space-950 hover:bg-aurora-400 transition-colors shadow-glow-cyan/20"
        >
          {action.label}
        </button>
      )}
    </GlassPanel>
  );
};
