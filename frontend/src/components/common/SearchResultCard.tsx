import React from 'react';
import { ArrowRight, BarChart3 } from 'lucide-react';
import { GlassPanel } from './GlassPanel';
import { TileThumbnail } from './TileThumbnail';
import { ScoreGauge } from './ScoreGauge';
import { formatCoord, formatDate } from '@/lib/utils';
import type { SearchResult } from '@/types/api';

interface SearchResultCardProps {
  result: SearchResult;
  index: number;
  onSelect: (result: SearchResult) => void;
  onAnalyze: (result: SearchResult) => void;
  onOpenZoom: (src: string | null | undefined) => void;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({
  result,
  index,
  onSelect,
  onAnalyze,
  onOpenZoom,
}) => (
  <GlassPanel
    hoverEffect
    className="group cursor-pointer space-y-3 p-3.5"
    onClick={() => onSelect(result)}
  >
    <div className="relative">
      <TileThumbnail
        src={result.thumbnail_url}
        alt={result.tile_id}
        aspectRatio="square"
        onOpenZoom={onOpenZoom}
        showZoomButton
      />
      <div className="absolute bottom-2 right-2 rounded-full border border-white/[0.1] bg-space-950/90 p-1 backdrop-blur-md">
        <ScoreGauge score={result.similarity} size={42} strokeWidth={3.5} />
      </div>
    </div>

    <div className="space-y-2 font-mono text-xs">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold text-text-primary">{result.tile_id}</div>
          <div className="text-[10px] uppercase text-text-muted">Result {index + 1}</div>
        </div>
        <span className="rounded border border-white/[0.08] bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-text-secondary">
          {result.aoi_name || result.aoi_id}
        </span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-text-muted">
        <span>{formatDate(result.date)}</span>
        <span>{formatCoord(result.lat)}, {formatCoord(result.lon)}</span>
      </div>
      <div className="flex items-center justify-between border-t border-white/[0.06] pt-2">
        <span className="text-[10px] uppercase text-text-muted">Similarity</span>
        <span className="font-semibold text-aurora-300">{result.similarity.toFixed(3)}</span>
      </div>
    </div>

    <div className="flex items-center justify-between border-t border-white/[0.06] pt-2">
      <button
        type="button"
        onClick={(event) => { event.stopPropagation(); onSelect(result); }}
        className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wide text-text-secondary transition hover:text-text-primary"
      >
        Inspect Result <ArrowRight size={12} />
      </button>
      {result.analysis_available ? (
        <button
          type="button"
          onClick={(event) => { event.stopPropagation(); onAnalyze(result); }}
          className="inline-flex items-center gap-1.5 rounded-md border border-aurora-500/30 bg-aurora-500/10 px-2 py-1 text-[10px] font-mono uppercase text-aurora-300 transition hover:bg-aurora-500/20"
        >
          <BarChart3 size={12} /> View Analysis
        </button>
      ) : (
        <span className="text-right text-[9px] font-mono uppercase text-text-muted">Temporal analysis unavailable</span>
      )}
    </div>
  </GlassPanel>
);
