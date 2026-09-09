import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { NdviPoint } from '@/types/api';
import { formatDate } from '@/lib/utils';

interface NDVIChartProps {
  series: NdviPoint[];
  beforeDate?: string;
  afterDate?: string;
  className?: string;
}

export const NDVIChart: React.FC<NDVIChartProps> = ({
  series,
  beforeDate,
  afterDate,
  className,
}) => {
  if (!series || series.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-text-muted text-xs font-mono">
        No multi-temporal spectral series available
      </div>
    );
  }

  // Sort series chronologically
  const chartData = [...series].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <div className={className || 'h-72 w-full'}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="cloudGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8B949E" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#8B949E" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          <XAxis
            dataKey="date"
            tickFormatter={(val) => formatDate(val)}
            stroke="#484F58"
            tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
          />
          <YAxis
            yAxisId="index"
            domain={[-0.5, 1]}
            stroke="#484F58"
            tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
          />
          <YAxis
            yAxisId="cloud"
            orientation="right"
            domain={[0, 1]}
            hide
          />

          <Tooltip
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="rounded-lg bg-space-950/90 border border-white/[0.1] p-3 shadow-glass backdrop-blur-md font-mono text-xs">
                    <p className="text-text-primary font-medium mb-1.5">{formatDate(label)}</p>
                    {payload.map((entry, idx) => (
                      <div key={idx} className="flex items-center justify-between gap-4 py-0.5">
                        <span style={{ color: entry.color }} className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                          {entry.name}:
                        </span>
                        <span className="text-text-primary font-semibold">
                          {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              }
              return null;
            }}
          />

          <Legend
            wrapperStyle={{
              paddingTop: '8px',
              fontFamily: 'JetBrains Mono',
              fontSize: '11px',
            }}
          />

          {beforeDate && (
            <ReferenceLine
              yAxisId="index"
              x={beforeDate}
              stroke="#8B949E"
              strokeDasharray="3 3"
              label={{ value: 'T1', fill: '#8B949E', fontSize: 10, position: 'top' }}
            />
          )}
          {afterDate && (
            <ReferenceLine
              yAxisId="index"
              x={afterDate}
              stroke="#00D4FF"
              strokeDasharray="3 3"
              label={{ value: 'T2', fill: '#00D4FF', fontSize: 10, position: 'top' }}
            />
          )}

          <Area
            yAxisId="cloud"
            type="monotone"
            dataKey="cloud_fraction"
            name="Cloud Cover"
            fill="url(#cloudGradient)"
            stroke="#8B949E"
            strokeDasharray="2 2"
          />
          <Line
            yAxisId="index"
            type="monotone"
            dataKey="ndvi_mean"
            name="NDVI (Vegetation)"
            stroke="#10B981"
            strokeWidth={2}
            dot={{ r: 3, fill: '#10B981' }}
            activeDot={{ r: 5, fill: '#34D399', stroke: '#06090E', strokeWidth: 2 }}
          />
          <Line
            yAxisId="index"
            type="monotone"
            dataKey="ndwi_mean"
            name="NDWI (Water)"
            stroke="#00D4FF"
            strokeWidth={2}
            dot={{ r: 3, fill: '#00D4FF' }}
            activeDot={{ r: 5, fill: '#22D3EE', stroke: '#06090E', strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
