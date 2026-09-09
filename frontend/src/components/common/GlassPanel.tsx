import React from 'react';
import { cn } from '@/lib/utils';
import { motion, type HTMLMotionProps } from 'framer-motion';

export interface GlassPanelProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
  glowColor?: 'cyan' | 'emerald' | 'rose' | 'none';
  variant?: 'default' | 'surface' | 'bordered';
  hasTopGradient?: boolean;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className,
  hoverEffect = false,
  glowColor = 'none',
  variant = 'default',
  hasTopGradient = true,
  ...props
}) => {
  const glowStyles = {
    none: '',
    cyan: 'shadow-glow-cyan/20 border-aurora-500/30',
    emerald: 'shadow-glow-emerald/20 border-emerald-500/30',
    rose: 'shadow-glow-rose/20 border-rose-500/30',
  }[glowColor];

  const variantStyles = {
    default: 'bg-white/[0.03] backdrop-blur-xl border border-white/[0.08]',
    surface: 'bg-[#0D1117]/80 backdrop-blur-xl border border-white/[0.06]',
    bordered: 'bg-white/[0.02] backdrop-blur-2xl border border-white/[0.12]',
  }[variant];

  return (
    <motion.div
      className={cn(
        'relative rounded-xl overflow-hidden transition-all duration-300',
        variantStyles,
        glowStyles,
        hoverEffect &&
          'hover:border-white/[0.18] hover:bg-white/[0.05] hover:shadow-glass hover:-translate-y-[2px]',
        className
      )}
      {...props}
    >
      {hasTopGradient && (
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.15] to-transparent pointer-events-none" />
      )}
      {children}
    </motion.div>
  );
};
