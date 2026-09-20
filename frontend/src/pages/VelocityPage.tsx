import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, Camera } from 'lucide-react';
import { useVelocity } from '@/hooks/useVelocity';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TemporalSignatureChart } from '@/components/common/TemporalSignatureChart';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { EmptyState } from '@/components/common/EmptyState';
import { formatDate } from '@/lib/utils';

export const VelocityPage: React.FC = () => {
  const navigate = useNavigate();
  const [limit, setLimit] = React.useState(8);
  const { data, isLoading, isError, refetch } = useVelocity(limit);
  const tiles = data?.filter((tile) => tile.series.length >= 2) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Velocity Signatures</h1>
        <p className="text-xs text-text-secondary mt-1 font-mono">Track how each location changes over time with real temporal evidence</p>
      </div>
      {isError && <ErrorCard title="Velocity Feed Unavailable" message="Could not retrieve temporal signatures." onRetry={() => refetch()} />}
      {isLoading ? <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{Array.from({ length: 4 }).map((_, index) => <SkeletonCard key={index} lines={5} />)}</div> : tiles.length === 0 ? <EmptyState icon={Activity} title="No Multi-Temporal Tiles" description="At least three observations are required to display a velocity signature." /> : <>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{tiles.map((tile) => <GlassPanel key={tile.tile_id} className="p-5 space-y-4"><div className="flex items-center justify-between"><button type="button" onClick={() => navigate(`/tiles/${tile.tile_id}`)} className="font-mono text-sm font-semibold text-text-primary hover:text-aurora-300">{tile.tile_id}</button><span className="text-[10px] font-mono text-text-muted">{tile.series.length} observations</span></div><TemporalSignatureChart series={tile.series} trend={tile.trend} /><div className="border-t border-white/[0.08] pt-3"><div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-text-muted"><Camera size={12} className="text-aurora-400" /> Temporal evolution</div><div className="mt-3 grid grid-cols-3 gap-2">{tile.series.slice(0, 3).map((point, idx) => <button key={`${tile.tile_id}-${idx}`} type="button" onClick={() => navigate(`/tiles/${tile.tile_id}`)} className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-2 text-left hover:border-aurora-500/40 transition-colors"><div className="text-[9px] uppercase text-text-muted">{idx === 0 ? 'Before' : idx === 1 ? 'Change' : 'Current'}</div><div className="mt-1 text-[10px] text-aurora-300">{point.velocity.toFixed(5)}</div><div className="mt-1 text-[9px] text-text-secondary">{formatDate(point.date_pair.before)} → {formatDate(point.date_pair.after)}</div></button>)}</div></div></GlassPanel>)}</div>
        <div className="flex justify-center pt-2">
          <button type="button" onClick={() => setLimit((current) => current + 8)} className="rounded-full border border-aurora-500/40 bg-aurora-500/10 px-4 py-2 text-xs font-mono uppercase tracking-[0.2em] text-aurora-300 hover:bg-aurora-500/20">Load more</button>
        </div>
        <GlassPanel className="p-5 overflow-x-auto"><table className="w-full text-left text-xs font-mono"><thead className="text-[10px] uppercase tracking-wider text-text-muted border-b border-white/[0.08]"><tr><th className="pb-3">Tile</th><th className="pb-3">Trend</th><th className="pb-3">Date pair</th><th className="pb-3">Velocity</th><th className="pb-3">Source</th><th className="pb-3">Open</th></tr></thead><tbody>{tiles.flatMap((tile) => tile.series.map((point, index) => <tr key={`${tile.tile_id}-${index}`} className="border-b border-white/[0.05] text-text-secondary"><td className="py-3 text-text-primary">{tile.tile_id}</td><td className="py-3 uppercase">{tile.trend.replace('_', ' ')}</td><td className="py-3">{formatDate(point.date_pair.before)} <ArrowRight size={11} className="inline mx-1" /> {formatDate(point.date_pair.after)}</td><td className="py-3 text-aurora-300">{point.velocity.toFixed(5)}</td><td className="py-3">{point.source}</td><td className="py-3"><button type="button" title="Open tile" onClick={() => navigate(`/tiles/${tile.tile_id}`)} className="text-aurora-400"><ArrowRight size={14} /></button></td></tr>))}</tbody></table></GlassPanel>
      </>}
    </div>
  );
};