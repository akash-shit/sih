import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ApiStatusIndicator } from '@/components/common/ApiStatusIndicator';
import { Menu, ChevronRight } from 'lucide-react';

interface TopbarProps {
  onOpenMobile: () => void;
}

const pageTitles: Record<string, { title: string; category: string }> = {
  '/dashboard': { title: 'Mission Dashboard', category: 'Overview' },
  '/aois': { title: 'Areas of Interest', category: 'Catalog' },
  '/search': { title: 'Semantic & Visual Search', category: 'Intelligence' },
  '/changes': { title: 'Change Detection', category: 'Surveillance' },
  '/review': { title: 'Review Queue', category: 'Human-in-the-Loop' },
  '/clusters': { title: 'Discovery Clusters', category: 'Unsupervised' },
  '/onboard': { title: 'Onboard AOI', category: 'Pipeline' },
  '/audit-log': { title: 'Analyst Audit Trail', category: 'Provenance' },
  '/settings': { title: 'System Settings', category: 'Configuration' },
};

export const Topbar: React.FC<TopbarProps> = ({ onOpenMobile }) => {
  const location = useLocation();
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(
        now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC'
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Determine current page title
  let currentMeta = pageTitles[location.pathname];
  if (!currentMeta) {
    if (location.pathname.startsWith('/aois/')) {
      currentMeta = { title: 'AOI Detail Inspection', category: 'Catalog' };
    } else if (location.pathname.startsWith('/changes/')) {
      currentMeta = { title: 'Candidate Evidence & Spectral Analysis', category: 'Surveillance' };
    } else if (location.pathname.startsWith('/clusters/')) {
      currentMeta = { title: 'Cluster Members Gallery', category: 'Unsupervised' };
    } else if (location.pathname.startsWith('/tiles/')) {
      currentMeta = { title: 'Tile Spectral Signature', category: 'Catalog' };
    } else {
      currentMeta = { title: 'Command Console', category: 'SkyAnalyst' };
    }
  }

  return (
    <header className="sticky top-0 z-20 h-14 bg-[#0A0E14]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 lg:px-8 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="p-1.5 rounded-lg lg:hidden hover:bg-white/[0.06] text-text-secondary hover:text-text-primary"
        >
          <Menu size={20} />
        </button>

        {/* Breadcrumb & Title */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-text-muted hidden sm:inline">{currentMeta.category}</span>
          <ChevronRight size={12} className="text-text-muted hidden sm:inline" />
          <h1 className="text-sm font-semibold text-text-primary tracking-tight font-sans">
            {currentMeta.title}
          </h1>
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 font-mono text-[11px] text-text-muted px-2.5 py-1 rounded-md bg-white/[0.02] border border-white/[0.04]">
          <span className="w-1.5 h-1.5 rounded-full bg-aurora-400" />
          {utcTime || 'Synchronizing…'}
        </div>
        <ApiStatusIndicator />
      </div>
    </header>
  );
};
