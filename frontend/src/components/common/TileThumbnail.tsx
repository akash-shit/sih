import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Satellite, ZoomIn } from 'lucide-react';

interface TileThumbnailProps {
  src?: string | null;
  alt?: string;
  className?: string;
  aspectRatio?: 'square' | 'video' | 'wide' | 'auto';
  zoomOnHover?: boolean;
  unavailable?: boolean;
  unavailableLabel?: string;
  onOpenZoom?: (src: string | null | undefined) => void;
  showZoomButton?: boolean;
}

export const TileThumbnail: React.FC<TileThumbnailProps> = ({
  src,
  alt = 'Satellite Imagery Tile',
  className,
  aspectRatio = 'square',
  zoomOnHover = true,
  unavailable = false,
  unavailableLabel = 'Source Imagery Unavailable',
  onOpenZoom,
  showZoomButton = false,
}) => {
  const [hasError, setHasError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const aspectClass = {
    square: 'aspect-square',
    video: 'aspect-video',
    wide: 'aspect-[16/10]',
    auto: '',
  }[aspectRatio];

  const showUnavailable = unavailable || !src;
  const showPlaceholder = showUnavailable || hasError;
  const canZoom = !!onOpenZoom && !!src && !showPlaceholder;

  return (
    <div
      className={cn(
        'relative overflow-hidden bg-space-850 border border-white/[0.06] rounded-lg group',
        aspectClass,
        className
      )}
    >
      {showPlaceholder ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-4 bg-gradient-to-br from-space-900 to-space-850 hud-grid-pattern">
          <div className="w-9 h-9 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-text-muted mb-2 transition-colors">
            <Satellite size={16} />
          </div>
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest text-center">
            {showUnavailable ? unavailableLabel : 'Render Pending'}
          </span>
          {!showUnavailable && <div className="absolute bottom-1.5 right-2 font-mono text-[9px] text-white/[0.2]">10m S2-L2A</div>}
        </div>
      ) : (
        <>
          {!isLoaded && (
            <div className="absolute inset-0 bg-white/[0.04] animate-pulse flex items-center justify-center">
              <Satellite size={16} className="text-white/20 animate-spin" />
            </div>
          )}
          <img
            src={src}
            alt={alt}
            loading="lazy"
            decoding="async"
            onLoad={() => setIsLoaded(true)}
            onError={() => setHasError(true)}
            onClick={(event) => {
              if (!canZoom) return;
              event.stopPropagation();
              onOpenZoom?.(src);
            }}
            className={cn(
              'w-full h-full object-cover transition-transform duration-300 cursor-pointer',
              zoomOnHover && 'group-hover:scale-105',
              isLoaded ? 'opacity-100' : 'opacity-0'
            )}
          />
          {canZoom && showZoomButton && (
            <button
              type="button"
              aria-label={`Zoom ${alt}`}
              onClick={(event) => {
                event.stopPropagation();
                onOpenZoom?.(src);
              }}
              className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-white/[0.12] bg-space-950/80 text-text-secondary shadow-lg transition hover:text-text-primary"
            >
              <ZoomIn size={12} />
            </button>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-space-950/70 via-transparent to-transparent pointer-events-none opacity-60 group-hover:opacity-30 transition-opacity" />
        </>
      )}
    </div>
  );
};
