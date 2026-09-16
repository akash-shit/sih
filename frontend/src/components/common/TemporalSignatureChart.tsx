import React from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { VelocityPoint } from '@/types/api';

interface TemporalSignatureChartProps {
  series?: VelocityPoint[];
  values?: number[];
  trend?: string;
  className?: string;
}

const trendStyles: Record<string, string> = {
  accelerating: 'text-rose-300 bg-rose-500/10 border-rose-500/30',
  steady_change: 'text-amber-300 bg-amber-500/10 border-amber-500/30',
  stable: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  decelerating: 'text-sky-300 bg-sky-500/10 border-sky-500/30',
};

export const TemporalSignatureChart: React.FC<TemporalSignatureChartProps> = ({ series, values, trend, className }) => {
  const data = series
    ? series.map((point, index) => ({ ...point, label: `${index + 1}` }))
    : (values || []).map((velocity, index) => ({ velocity, label: `${index + 1}` }));
  const label = (trend || 'stable').replace('_', ' ').toUpperCase();

  return (
    <div className={className || 'h-48 w-full'}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Velocity curve</span>
        <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-semibold ${trendStyles[trend || 'stable'] || trendStyles.stable}`}>{label}</span>
      </div>
      {data.length === 0 ? (
        <div className="h-36 flex items-center justify-center text-xs font-mono text-text-muted">No velocity observations</div>
      ) : (
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
            <XAxis dataKey="label" stroke="#484F58" tick={{ fill: '#8B949E', fontSize: 10 }} tickLine={false} />
            <YAxis stroke="#484F58" tick={{ fill: '#8B949E', fontSize: 10 }} tickLine={false} />
            <Tooltip content={({ active, payload }) => active && payload?.length ? <div className="rounded-lg bg-space-950/90 border border-white/[0.1] p-2 font-mono text-[10px]">Velocity: {Number(payload[0].value).toFixed(5)}</div> : null} />
            <Line type="monotone" dataKey="velocity" stroke="#00D4FF" strokeWidth={2} dot={{ r: 3, fill: '#00D4FF' }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};