import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Map,
  Search,
  Radar,
  ClipboardCheck,
  Network,
  FolderPlus,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Satellite,
  Activity,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
}

const mainNavItems: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Areas of Interest', path: '/aois', icon: Map },
  { label: 'Semantic Search', path: '/search', icon: Search },
  { label: 'Change Detection', path: '/changes', icon: Radar },
  { label: 'Velocity', path: '/velocity', icon: Activity },
  { label: 'Review Queue', path: '/review', icon: ClipboardCheck },
  { label: 'Discovery Clusters', path: '/clusters', icon: Network },
  { label: 'Onboard AOI', path: '/onboard', icon: FolderPlus },
  { label: 'Audit Log', path: '/audit-log', icon: ScrollText },
];

const secondaryNavItems: NavItem[] = [
  { label: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggle,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const navigate = useNavigate();

  const handleSignOut = () => {
    navigate('/signin');
  };

  const navContent = (
    <div className="flex flex-col h-full justify-between select-none">
      {/* Top Header */}
      <div>
        <div className="h-14 flex items-center justify-between px-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-aurora-500/10 border border-aurora-500/30 flex items-center justify-center text-aurora-400 shrink-0 shadow-glow-cyan/20">
              <Satellite size={18} />
            </div>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                className="flex flex-col"
              >
                <span className="font-mono text-sm font-semibold tracking-tight text-text-primary flex items-center gap-1.5">
                  SkyAnalyst
                  <span className="text-[9px] px-1 py-0.2 rounded bg-aurora-500/20 text-aurora-300 font-mono">
                    SIH
                  </span>
                </span>
                <span className="text-[10px] text-text-muted font-mono tracking-wider uppercase">
                  GEOINT COMMAND
                </span>
              </motion.div>
            )}
          </div>

          <button
            onClick={onToggle}
            className="hidden lg:flex w-6 h-6 items-center justify-center rounded-md bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary hover:text-text-primary transition-colors border border-white/[0.06]"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-2 space-y-1 mt-2">
          {mainNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  cn(
                    'relative flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group',
                    isActive
                      ? 'text-aurora-300 font-semibold bg-aurora-500/10 border border-aurora-500/20 shadow-glow-cyan/10'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      className={cn(
                        'shrink-0 transition-colors',
                        isActive
                          ? 'text-aurora-400'
                          : 'text-text-muted group-hover:text-text-primary'
                      )}
                    />
                    {!collapsed && (
                      <span className="truncate tracking-wide">{item.label}</span>
                    )}
                    {isActive && (
                      <motion.div
                        layoutId="activeNavIndicator"
                        className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-aurora-400 shadow-[0_0_8px_#00D4FF]"
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}

          <div className="pt-2 pb-1">
            <div className="h-px bg-white/[0.06] mx-2" />
          </div>

          {secondaryNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  cn(
                    'relative flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group',
                    isActive
                      ? 'text-aurora-300 font-semibold bg-aurora-500/10 border border-aurora-500/20'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      className={cn(
                        'shrink-0 transition-colors',
                        isActive
                          ? 'text-aurora-400'
                          : 'text-text-muted group-hover:text-text-primary'
                      )}
                    />
                    {!collapsed && (
                      <span className="truncate tracking-wide">{item.label}</span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* User Profile Footer */}
      <div className="p-3 border-t border-white/[0.06]">
        <div
          className={cn(
            'flex items-center rounded-xl p-2 bg-white/[0.02] border border-white/[0.06]',
            collapsed ? 'justify-center' : 'justify-between'
          )}
        >
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-aurora-500/20 to-purple-500/20 border border-white/[0.12] flex items-center justify-center text-xs font-mono font-bold text-aurora-300 shrink-0">
              AB
            </div>
            {!collapsed && (
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-medium text-text-primary truncate">
                  Analyst Base
                </span>
                <span className="text-[10px] font-mono text-text-muted truncate">
                  analyst@skyanalyst.in
                </span>
              </div>
            )}
          </div>

          {!collapsed && (
            <button
              onClick={handleSignOut}
              className="p-1.5 rounded-lg hover:bg-white/[0.06] text-text-muted hover:text-rose-400 transition-colors"
              title="Sign Out"
            >
              <LogOut size={15} />
            </button>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Fixed Sidebar */}
      <aside
        className={cn(
          'hidden lg:block fixed left-0 top-0 bottom-0 z-30 bg-[#0A0E14]/95 backdrop-blur-xl border-r border-white/[0.06] transition-all duration-300',
          collapsed ? 'w-[72px]' : 'w-[260px]'
        )}
      >
        {navContent}
      </aside>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onCloseMobile}
              className="absolute inset-0 bg-space-950/80 backdrop-blur-sm"
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute left-0 top-0 bottom-0 w-[260px] bg-[#0A0E14] border-r border-white/[0.08] shadow-2xl z-10"
            >
              {navContent}
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};
