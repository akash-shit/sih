import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Minus, Plus, RotateCcw, X, ZoomIn } from 'lucide-react';
import { cn } from '@/lib/utils';
import { GlassPanel } from './GlassPanel';

interface ImageZoomModalProps {
  src: string | null | undefined;
  alt?: string;
  open: boolean;
  onClose: () => void;
}

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export const ImageZoomModal: React.FC<ImageZoomModalProps> = ({
  src,
  alt = 'Satellite image zoom',
  open,
  onClose,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  const [fitScale, setFitScale] = useState(1);
  const [zoom, setZoom] = useState(1);

  const resetState = () => {
    setZoom(1);
  };

  const updateFitScale = () => {
    const container = containerRef.current;
    const image = imageRef.current;
    if (!container || !image?.naturalWidth || !image.naturalHeight) return;
    const bounds = container.getBoundingClientRect();
    setFitScale(Math.min(bounds.width / image.naturalWidth, bounds.height / image.naturalHeight));
  };

  useEffect(() => {
    if (!open) return;
    resetState();
  }, [open, src]);

  useEffect(() => {
    if (!open) return;
    updateFitScale();
    const observer = new ResizeObserver(updateFitScale);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [open, src]);

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  const zoomBy = (nextScale: number) => setZoom(clamp(nextScale, 1, 6));

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    if (!open || !containerRef.current) return;
    const direction = event.deltaY > 0 ? 0.9 : 1.1;
    zoomBy(zoom * direction);
  };

  const zoomPercent = useMemo(() => Math.round(zoom * 100), [zoom]);

  if (!src) return null;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-space-950/85 backdrop-blur-sm p-3"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full max-w-6xl max-h-[92vh]"
            onClick={(event) => event.stopPropagation()}
          >
            <GlassPanel className="relative h-full w-full overflow-hidden border-white/[0.12] bg-space-900/90 shadow-2xl">
              <button
                type="button"
                aria-label="Close image zoom"
                onClick={onClose}
                className="absolute right-3 top-3 z-20 flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.12] bg-space-950/80 text-text-secondary transition hover:text-text-primary"
              >
                <X size={16} />
              </button>

              <div
                ref={containerRef}
                className={cn(
                  'relative h-full w-full overflow-hidden overscroll-contain bg-black/40'
                )}
                onWheel={handleWheel}
              >
                <img
                  ref={imageRef}
                  src={src}
                  alt={alt}
                  onLoad={updateFitScale}
                  className="absolute left-1/2 top-1/2 select-none transition-transform duration-75 ease-out"
                  style={{
                    transform: `translate(-50%, -50%) scale(${fitScale * zoom})`,
                    maxWidth: 'none',
                    maxHeight: 'none',
                    width: 'auto',
                    height: 'auto',
                    cursor: 'default',
                  }}
                />

                <div className="absolute bottom-4 right-4 z-20 flex items-center gap-2 rounded-full border border-white/[0.12] bg-space-950/80 px-2 py-1.5 shadow-xl backdrop-blur-md">
                  <button
                    type="button"
                    aria-label="Zoom out"
                    onClick={() => zoomBy(zoom * 0.9)}
                    className="flex h-8 w-8 items-center justify-center rounded-full text-text-secondary hover:bg-white/[0.06] hover:text-text-primary"
                  >
                    <Minus size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label="Zoom in"
                    onClick={() => zoomBy(zoom * 1.1)}
                    className="flex h-8 w-8 items-center justify-center rounded-full text-text-secondary hover:bg-white/[0.06] hover:text-text-primary"
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label="Reset zoom"
                    onClick={resetState}
                    className="flex h-8 w-8 items-center justify-center rounded-full text-text-secondary hover:bg-white/[0.06] hover:text-text-primary"
                  >
                    <RotateCcw size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label="Fit image"
                    onClick={resetState}
                    className="px-2 text-[10px] font-mono text-text-secondary hover:text-text-primary"
                  >
                    FIT
                  </button>
                  <div className="min-w-[58px] border-l border-white/[0.08] pl-2 text-center font-mono text-[10px] text-aurora-300">
                    {zoomPercent}%
                  </div>
                </div>

                <div className="absolute left-4 top-4 z-20 inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-space-950/70 px-2.5 py-1.5 text-[10px] font-mono text-text-secondary backdrop-blur-md">
                  <ZoomIn size={12} className="text-aurora-400" />
                  Scroll to zoom
                </div>
              </div>
            </GlassPanel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
