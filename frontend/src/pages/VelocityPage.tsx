import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight } from 'lucide-react';
import { useVelocity } from '@/hooks/useVelocity';
import { GlassPanel } from '@/components/common/GlassPanel';
import { TemporalSignatureChart } from '@/components/common/TemporalSignatureChart';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { ErrorCard } from '@/components/common/ErrorCard';
import { EmptyState } from '@/components/common/EmptyState';
import { formatDate } from '@/lib/utils';

export const VelocityPage: React.FC = () => {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useVelocity();
  const tiles = data?.filter((tile) => tile.series.length >= 2) || [];

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight text-text-primary">Velocity Signatures</h1><p className="text-xs text-text-secondary mt-1 font-mono">Chronological change rate across monitored ground cells</p></div>
      {isError && <ErrorCard title="Velocity Feed Unavailable" message="Could not retrieve temporal signatures." onRetry={() => refetch()} />}
      {isLoading ? <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{Array.from({ length: 4 }).map((_, index) => <SkeletonCard key={index} lines={5} />)}</div> : tiles.length === 0 ? <EmptyState icon={Activity} title="No Multi-Temporal Tiles" description="At least three observations are required to display a velocity signature." /> : <>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{tiles.map((tile) => <GlassPanel key={tile.tile_id} className="p-5 space-y-4"><div className="flex items-center justify-between"><button type="button" onClick={() => navigate(`/tiles/${tile.tile_id}`)} className="font-mono text-sm font-semibold text-text-primary hover:text-aurora-300">{tile.tile_id}</button><span className="text-[10px] font-mono text-text-muted">{tile.series.length + 1} observations</span></div><TemporalSignatureChart series={tile.series} trend={tile.trend} /></GlassPanel>)}</div>
        <GlassPanel className="p-5 overflow-x-auto"><table className="w-full text-left text-xs font-mono"><thead className="text-[10px] uppercase tracking-wider text-text-muted border-b border-white/[0.08]"><tr><th className="pb-3">Tile</th><th className="pb-3">Trend</th><th className="pb-3">Date pair</th><th className="pb-3">Velocity</th><th className="pb-3">Source</th><th className="pb-3">Open</th></tr></thead><tbody>{tiles.flatMap((tile) => tile.series.map((point, index) => <tr key={`${tile.tile_id}-${index}`} className="border-b border-white/[0.05] text-text-secondary"><td className="py-3 text-text-primary">{tile.tile_id}</td><td className="py-3 uppercase">{tile.trend.replace('_', ' ')}</td><td className="py-3">{formatDate(point.date_pair.before)} <ArrowRight size={11} className="inline mx-1" /> {formatDate(point.date_pair.after)}</td><td className="py-3 text-aurora-300">{point.velocity.toFixed(5)}</td><td className="py-3">{point.source}</td><td className="py-3"><button type="button" title="Open tile" onClick={() => navigate(`/tiles/${tile.tile_id}`)} className="text-aurora-400"><ArrowRight size={14} /></button></td></tr>))}</tbody></table></GlassPanel>
      </>}
    </div>
  );
};