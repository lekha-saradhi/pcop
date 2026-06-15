'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Eye, EyeOff, AlertCircle, TrendingUp, Activity, Shield, Brain } from 'lucide-react';

const DEMO = [
  { user: 'analyst',  pass: 'analyst123',  role: 'Risk Analyst',       desc: 'Read-only · signals & analytics' },
  { user: 'manager',  pass: 'manager123',  role: 'Portfolio Manager',  desc: 'Campaigns · review approvals'   },
  { user: 'admin',    pass: 'admin123',    role: 'Administrator',      desc: 'Full platform access'           },
];

const STATS = [
  { icon: Brain,      value: '0.93',  label: 'GraphSAGE AUC' },
  { icon: Activity,   value: '9',     label: 'Signal Streams' },
  { icon: Shield,     value: '7',     label: 'AI/ML Layers'  },
  { icon: TrendingUp, value: '< 4h',  label: 'Detection Lag' },
];

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState('');
  const { login } = useAuth();
  const router    = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      router.push('/dashboard');
    } catch {
      setError('Invalid credentials. Try the demo accounts below.');
    } finally {
      setLoading(false);
    }
  };

  const fill = (u: string, p: string) => { setUsername(u); setPassword(p); setError(''); };

  return (
    <div className="w-full min-h-screen flex" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

      {/* ── Left panel — dark branding ──────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[52%] flex-col justify-between relative overflow-hidden"
           style={{ background: 'linear-gradient(145deg, #06112a 0%, #0f2d5c 60%, #0c2347 100%)' }}>

        {/* Grid overlay */}
        <div className="absolute inset-0 opacity-[0.06]"
             style={{ backgroundImage: 'linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)', backgroundSize: '48px 48px' }} />

        {/* Glow blob */}
        <div className="absolute top-[-120px] right-[-120px] w-[500px] h-[500px] rounded-full opacity-20"
             style={{ background: 'radial-gradient(circle, #38bdf8 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-80px] left-[-80px] w-[400px] h-[400px] rounded-full opacity-10"
             style={{ background: 'radial-gradient(circle, #818cf8 0%, transparent 70%)' }} />

        {/* Content */}
        <div className="relative z-10 p-12 flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-auto">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                 style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)' }}>
              <span className="text-white text-[12px] font-black tracking-tight">NG</span>
            </div>
            <div>
              <p className="text-white text-[15px] font-bold tracking-tight leading-none">PCOP</p>
              <p className="text-white/40 text-[10px] tracking-widest uppercase mt-0.5">NextGenHacks</p>
            </div>
          </div>

          {/* Hero text */}
          <div className="my-auto">
            <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full"
                 style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.25)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="text-sky-300 text-[10px] font-semibold uppercase tracking-widest">NextGenHacks · AI Innovation 2026</span>
            </div>

            <h1 className="text-white font-black leading-[1.05] mb-4"
                style={{ fontSize: 'clamp(2.2rem, 3.5vw, 3.2rem)', letterSpacing: '-0.02em' }}>
              Predict.<br />Personalise.<br />
              <span style={{ WebkitTextStroke: '1px rgba(255,255,255,0.4)', color: 'transparent' }}>Retain.</span>
            </h1>

            <p className="text-white/50 text-[14px] leading-relaxed max-w-[380px]">
              Seven-layer AI/ML platform identifying retail banking customers at risk of attrition — weeks before any explicit signal.
            </p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3 mt-auto">
            {STATS.map(s => (
              <div key={s.label} className="rounded-xl p-4"
                   style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <s.icon className="w-4 h-4 text-sky-400 mb-2" />
                <p className="text-white text-[22px] font-black leading-none">{s.value}</p>
                <p className="text-white/40 text-[10px] mt-1 uppercase tracking-wider">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Footer */}
          <p className="text-white/20 text-[10px] mt-8 uppercase tracking-widest">
            NextGenHacks · AI Innovation · 2026
          </p>
        </div>
      </div>

      {/* ── Right panel — login form ────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center bg-[#F7F8FC] px-6 py-12">
        {/* Mobile logo */}
        <div className="flex lg:hidden items-center gap-2.5 mb-10">
          <div className="w-8 h-8 rounded-lg bg-[#0f2d5c] flex items-center justify-center">
            <span className="text-white text-[10px] font-black">NG</span>
          </div>
          <span className="text-[#0f2d5c] text-[15px] font-bold">PCOP · NextGenHacks</span>
        </div>

        <div className="w-full max-w-[400px]">
          <h2 className="text-[28px] font-black text-slate-900 mb-1" style={{ letterSpacing: '-0.02em' }}>
            Welcome back
          </h2>
          <p className="text-slate-400 text-[14px] mb-8">Sign in to the intelligence platform</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-[12px] font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="analyst / manager / admin"
                required autoFocus autoComplete="username"
                className="w-full px-4 py-3 text-[14px] rounded-xl border bg-white text-slate-900 placeholder:text-slate-300 outline-none transition-all"
                style={{ borderColor: username ? '#0f2d5c' : '#e2e8f0', boxShadow: username ? '0 0 0 3px rgba(15,45,92,0.08)' : 'none' }}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-[12px] font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required autoComplete="current-password"
                  className="w-full px-4 py-3 pr-11 text-[14px] rounded-xl border bg-white text-slate-900 placeholder:text-slate-300 outline-none transition-all"
                  style={{ borderColor: password ? '#0f2d5c' : '#e2e8f0', boxShadow: password ? '0 0 0 3px rgba(15,45,92,0.08)' : 'none' }}
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500 transition-colors">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-red-50 border border-red-100">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-[13px] text-red-600">{error}</span>
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={loading || !username || !password}
              className="w-full py-3.5 rounded-xl text-[14px] font-bold text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed mt-2"
              style={{ background: 'linear-gradient(135deg, #0f2d5c 0%, #1d4ed8 100%)', boxShadow: '0 4px 16px rgba(15,45,92,0.3)' }}>
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in…
                </span>
              ) : 'Sign In'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-8">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-[11px] text-slate-400 uppercase tracking-widest">Demo accounts</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          {/* Demo accounts */}
          <div className="space-y-2">
            {DEMO.map(d => (
              <button key={d.user} onClick={() => fill(d.user, d.pass)}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-[#0f2d5c]/30 hover:bg-slate-50 transition-all text-left group">
                <div className="w-8 h-8 rounded-lg bg-[#0f2d5c]/8 flex items-center justify-center shrink-0">
                  <span className="text-[#0f2d5c] text-[10px] font-black">{d.user.slice(0,2).toUpperCase()}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-bold text-slate-800 group-hover:text-[#0f2d5c] transition-colors">{d.role}</p>
                  <p className="text-[11px] text-slate-400">{d.desc}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[11px] font-mono font-semibold text-slate-500">{d.user}</p>
                  <p className="text-[10px] text-slate-300 group-hover:text-sky-500 transition-colors">click to fill →</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
