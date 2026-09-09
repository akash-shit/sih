import React, { useState } from 'react';
import { GlassPanel } from '@/components/common/GlassPanel';
import { useStats } from '@/hooks/useStats';
import { api } from '@/lib/api';
import {
  Server,
  Moon,
  Sun,
  CheckCircle,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { data: stats } = useStats();
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  const techStack = [
    { name: 'React 18', type: 'Frontend Framework' },
    { name: 'Vite 6', type: 'Bundler & Dev Server' },
    { name: 'TypeScript', type: 'Strict Type System' },
    { name: 'Tailwind CSS', type: 'Defense Glassmorphism' },
    { name: 'Framer Motion', type: 'Telemetry Animations' },
    { name: 'TanStack Query v5', type: 'API State Caching' },
    { name: 'Recharts', type: 'NDVI Time Series' },
    { name: 'RemoteCLIP ViT-B-32', type: '512-dim Embeddings' },
    { name: 'FAISS', type: 'Vector Similarity Index' },
    { name: 'FastAPI', type: 'Backend Microservice' },
    { name: 'SQLite', type: 'Catalog & Provenance DB' },
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">
          System & Pipeline Settings
        </h1>
        <p className="text-xs text-text-secondary mt-1 font-mono">
          Inspection of backend connection endpoints, model versions, and environmental flags
        </p>
      </div>

      {/* Section 1: Backend Connection & Processing Engine */}
      <GlassPanel className="p-6 space-y-5">
        <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
          <Server size={14} className="text-aurora-400" />
          Backend Service Configuration (Read-Only)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
            <span className="text-[10px] uppercase text-text-muted">API Base URL</span>
            <div className="text-text-primary font-semibold truncate flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              {api.baseUrl}
            </div>
            <p className="text-[10px] text-text-muted">Configured via VITE_API_BASE_URL</p>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
            <span className="text-[10px] uppercase text-text-muted">Processing Engine Version</span>
            <div className="text-text-primary font-semibold">
              {stats?.processing_version || 'v0.1-prototype'}
            </div>
            <p className="text-[10px] text-text-muted">Multi-spectral 19-stage pipeline build</p>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
            <span className="text-[10px] uppercase text-text-muted">Tile Resolution</span>
            <div className="text-text-primary font-semibold">224 x 224 px · 2.24 km footprint</div>
            <p className="text-[10px] text-text-muted">Sentinel-2 10m Ground Sample Distance</p>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1">
            <span className="text-[10px] uppercase text-text-muted">Offline Execution Mode</span>
            <div className="text-emerald-400 font-semibold flex items-center gap-1.5">
              <CheckCircle size={14} />
              Enforced (No External LLM / Cloud Calls)
            </div>
            <p className="text-[10px] text-text-muted">Satisfies SIH 26227 offline mandate</p>
          </div>
        </div>
      </GlassPanel>

      {/* Section 2: Appearance & Theme */}
      <GlassPanel className="p-6 space-y-4">
        <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary flex items-center gap-2">
          <Moon size={14} className="text-violet-light" />
          Console Appearance
        </h3>

        <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <div>
            <span className="text-xs font-semibold text-text-primary block font-mono">
              Mission Control Dark Mode
            </span>
            <span className="text-[11px] text-text-secondary">
              High-contrast defense theme engineered for satellite telemetry and optical analysis
            </span>
          </div>

          <div className="flex items-center gap-2 p-1 rounded-xl bg-space-950 border border-white/[0.08] font-mono text-xs">
            <button
              onClick={() => setTheme('dark')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                theme === 'dark'
                  ? 'bg-aurora-500/20 text-aurora-300 border border-aurora-500/30'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <Moon size={12} />
              Dark
            </button>
            <button
              onClick={() => setTheme('light')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                theme === 'light'
                  ? 'bg-aurora-500/20 text-aurora-300 border border-aurora-500/30'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <Sun size={12} />
              Light
            </button>
          </div>
        </div>
      </GlassPanel>

      {/* Section 3: About Project & SIH PS 26227 */}
      <GlassPanel className="p-6 space-y-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-lg">🛰️</span>
              <h3 className="text-base font-bold text-text-primary font-mono">SkyAnalyst Platform</h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-aurora-500/10 text-aurora-300 border border-aurora-500/20">
                SIH 2025
              </span>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed max-w-xl">
              Developed for Smart India Hackathon (Problem Statement 26227). Designed for high-cadence
              geospatial reconnaissance, automated infrastructure monitoring, deforestation detection,
              and multi-temporal environmental surveillance.
            </p>
          </div>
        </div>

        {/* Tech Stack Badges */}
        <div className="space-y-2 pt-2">
          <span className="text-[10px] font-mono uppercase text-text-muted block">
            Architecture Stack
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {techStack.map((tech) => (
              <div
                key={tech.name}
                className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06] font-mono text-xs flex flex-col"
              >
                <span className="text-text-primary font-semibold">{tech.name}</span>
                <span className="text-[10px] text-text-muted">{tech.type}</span>
              </div>
            ))}
          </div>
        </div>
      </GlassPanel>
    </div>
  );
};
