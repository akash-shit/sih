import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Satellite, ArrowRight, ShieldCheck, KeyRound, Mail, Orbit, Globe2 } from 'lucide-react';

export const SignInPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('analyst@skyanalyst.in');
  const [password, setPassword] = useState('••••••••••••');
  const [isBooting, setIsBooting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsBooting(true);
    setTimeout(() => {
      navigate('/dashboard');
    }, 400);
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#03070D] text-text-primary">
      <div className="space-scene" aria-hidden="true">
        <div className="space-stars space-stars-primary" />
        <div className="space-stars space-stars-secondary" />
        <div className="space-nebula" />
        <div className="space-earth-image" />
        <div className="space-atmosphere" />
        <div className="space-orbit-ring space-orbit-ring-one"><div className="space-satellite"><Satellite size={18} /></div></div>
        <div className="space-orbit-ring space-orbit-ring-two" />
      </div>

      <div className="relative z-10 flex min-h-screen items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 220, damping: 20 }}
          className="signin-glass w-full max-w-5xl rounded-[28px] border border-white/[0.08] bg-[#061018]/70 p-6 shadow-[0_0_40px_rgba(20,120,188,0.15)] backdrop-blur-xl"
        >
          <div className="grid items-center gap-8 md:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-[0.28em] text-cyan-200">
                <span className="inline-flex h-2 w-2 rounded-full bg-cyan-400" />
                Mission Ready
              </div>

              <div className="space-y-3">
                <div className="text-[11px] font-mono uppercase tracking-[0.36em] text-slate-300/80">
                  Earth Observation
                </div>
                <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
                  SENTINEL<br />INTELLIGENCE
                </h1>
              </div>

              <p className="max-w-xl text-sm text-slate-300 md:text-base">
                Satellite analysis & change detection for geospatial mission planning,
                temporal anomaly review, and semantic retrieval across real AOI archives.
              </p>

              <div className="grid gap-2 text-[11px] font-mono text-slate-200/85 md:max-w-md">
                {[
                  ['DATA LINK', 'ONLINE'],
                  ['GEOSPATIAL ENGINE', 'READY'],
                  ['SEMANTIC SEARCH', 'READY'],
                  ['CHANGE ENGINE', 'READY'],
                  ['ANALYTICS', 'READY'],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
                    <span className="text-slate-400">{label}</span>
                    <span className="text-cyan-300">{value}</span>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="inline-flex items-center gap-3 rounded-xl bg-cyan-400 px-5 py-3 text-xs font-mono font-medium uppercase tracking-[0.22em] text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.35)] transition hover:bg-cyan-300"
              >
                ENTER MISSION CONTROL
                <ArrowRight size={15} />
              </button>
            </div>

            <motion.div
              initial={{ opacity: 0, x: 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="relative"
            >
              <div className="signin-glass rounded-[24px] border border-white/[0.08] bg-[#0B1420]/80 p-6 shadow-[0_0_35px_rgba(16,185,129,0.08)] backdrop-blur-xl">
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-2 text-cyan-300">
                      <Satellite size={18} />
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">SkyAnalyst</div>
                      <div className="text-lg font-bold text-white">Mission Console</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-mono text-emerald-300">
                    <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                    ONLINE
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-slate-400">
                      <span>Telemetry</span>
                      <span>Nominal</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm text-slate-200">
                      <div className="rounded-xl border border-white/[0.06] bg-slate-950/50 p-3">
                        <div className="mb-2 flex items-center gap-2 text-cyan-300"><Globe2 size={14} /> AOIs</div>
                        <div className="text-xl font-semibold text-white">{3}</div>
                      </div>
                      <div className="rounded-xl border border-white/[0.06] bg-slate-950/50 p-3">
                        <div className="mb-2 flex items-center gap-2 text-violet-300"><Orbit size={14} /> Tiles</div>
                        <div className="text-xl font-semibold text-white">Realtime</div>
                      </div>
                    </div>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="relative">
                      <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full rounded-xl border border-white/[0.08] bg-slate-950/60 py-2.5 pl-10 pr-3 text-xs text-white outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-400/60"
                        placeholder="analyst@skyanalyst.in"
                      />
                    </div>
                    <div className="relative">
                      <KeyRound size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full rounded-xl border border-white/[0.08] bg-slate-950/60 py-2.5 pl-10 pr-3 text-xs tracking-[0.35em] text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/60"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isBooting}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-sky-500 px-4 py-3 text-xs font-mono uppercase tracking-[0.2em] text-slate-950 transition hover:brightness-110 disabled:opacity-70"
                    >
                      {isBooting ? 'Booting…' : 'Access Console'}
                      {!isBooting && <ArrowRight size={14} />}
                    </button>
                  </form>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>

      <div className="absolute bottom-4 right-4 z-10 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-[#061018]/80 px-3 py-1.5 text-[10px] font-mono uppercase tracking-[0.2em] text-slate-300">
        <ShieldCheck size={12} className="text-cyan-300" />
        SIH 2026
      </div>
    </div>
  );
};
