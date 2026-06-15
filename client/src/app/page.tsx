'use client';

import Link from 'next/link';
import { ArrowRight, Shield, Activity, Brain, Plug, CheckCircle2, AlertCircle, Code2, ChevronDown } from 'lucide-react';

const LAYERS = [
  { id: 'L1', name: 'INGEST',   color: '#0c2347', desc: 'Kafka · T24/Finacle · CRM · Mobile App' },
  { id: 'L2', name: 'ARGUS',    color: '#0f2d5c', desc: 'Shiryaev-Roberts · CUSUM · SPRT · 9 streams' },
  { id: 'L3', name: 'CHRONOS',  color: '#1a3f8f', desc: 'GENESIS · HABITAT · TARE · GraphSAGE · FusionXV2' },
  { id: 'L4', name: 'COMPASS',  color: '#0891b2', desc: 'LangGraph · Life-event inference · Next-best-action' },
  { id: 'L5', name: 'HERALD',   color: '#6d28d9', desc: 'NVIDIA DeepSeek V4 Pro · Email · SMS · Push' },
  { id: 'L6', name: 'VERDICT',  color: '#059669', desc: 'Doubly-robust ATE · Qini curve · Hillstrom' },
  { id: 'L7', name: 'ORACLE',   color: '#b45309', desc: 'Thompson Sampling · Weekly retrain · Prompt optimisation' },
];

const REAL = [
  { real: true,  text: 'All 7 AI/ML layers fully designed, documented and implemented' },
  { real: true,  text: 'ARGUS algorithms (SR, CUSUM, SPRT) — real statistical implementations' },
  { real: true,  text: 'CHRONOS 5-model ensemble with conformal prediction intervals' },
  { real: true,  text: 'HERALD content generation via live NVIDIA DeepSeek V4 Pro API' },
  { real: true,  text: 'VERDICT doubly-robust ATE estimator and Qini uplift curves' },
  { real: true,  text: 'REST API — any banking portal can integrate with one endpoint' },
  { real: false, text: '50 customers are synthetic — scores pre-computed for demo' },
  { real: false, text: 'No live bank feed — Kafka events simulated every 8 seconds' },
];

const SIGNALS = [
  { type: 'Balance Decline',      method: 'CUSUM', conf: 91, desc: 'Sustained balance drop over 6 weeks — CUSUM detects the downward regime shift before it reaches zero.' },
  { type: 'Salary Credit Miss',   method: 'SPRT',  conf: 88, desc: 'No salary credit for 2 consecutive months — Wald sequential test fires after the second absence.' },
  { type: 'App Login Drop',       method: 'SR',    conf: 84, desc: '18 → 2 logins/month — Shiryaev-Roberts detects the engagement regime change instantly.' },
  { type: 'Complaint Spike',      method: 'SPRT',  conf: 97, desc: '3 complaints in 30d vs. 0.2/month baseline — Poisson SPRT fires after the first abnormal count.' },
  { type: 'Competitor Transfer',  method: 'CUSUM', conf: 79, desc: 'Recurring ₹50K outward IMPS to HDFC — CUSUM detects the new periodic outflow pattern.' },
  { type: 'Dormancy',             method: 'SR',    conf: 95, desc: '45+ days zero transactions — SR detects step-change from active-customer prior in one pass.' },
];

const CREDS = [
  { user: 'analyst', pass: 'analyst123', role: 'Risk Analyst',      access: 'Signals · scores · analytics (read-only)' },
  { user: 'manager', pass: 'manager123', role: 'Portfolio Manager', access: 'Campaigns · review queue · approvals' },
  { user: 'admin',   pass: 'admin123',   role: 'Administrator',     access: 'Full platform access' },
];

const METHOD: Record<string, string> = {
  SR: 'bg-blue-100 text-blue-700', CUSUM: 'bg-orange-100 text-orange-700', SPRT: 'bg-purple-100 text-purple-700',
};

export default function LandingPage() {
  return (
    <div className="w-full min-h-screen bg-white text-slate-900" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

      {/* ── NAV ─────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-white/10"
           style={{ background: 'rgba(6,17,42,0.92)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center">
              <span className="text-white text-[9px] font-black">NG</span>
            </div>
            <span className="text-white text-[14px] font-bold">PCOP</span>
            <span className="text-white/30 text-[10px] font-semibold px-2 py-0.5 rounded border border-white/10 uppercase tracking-wider ml-1">Demo</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#how-it-works" className="text-white/50 hover:text-white text-[13px] transition-colors hidden md:block">How it works</a>
            <a href="#architecture" className="text-white/50 hover:text-white text-[13px] transition-colors hidden md:block">Architecture</a>
            <a href="#api" className="text-white/50 hover:text-white text-[13px] transition-colors hidden md:block">API</a>
            <Link href="/login"
              className="flex items-center gap-1.5 text-[13px] font-semibold px-4 py-2 rounded-lg text-white transition-all"
              style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)' }}>
              Enter Platform <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center text-center overflow-hidden pt-14"
               style={{ background: 'linear-gradient(160deg, #06112a 0%, #0f2d5c 50%, #0a1f45 100%)' }}>

        {/* Background grid */}
        <div className="absolute inset-0 opacity-[0.07]"
             style={{ backgroundImage: 'linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)', backgroundSize: '56px 56px' }} />

        {/* Glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full opacity-15 pointer-events-none"
             style={{ background: 'radial-gradient(circle, #38bdf8 0%, transparent 65%)' }} />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full opacity-10 pointer-events-none"
             style={{ background: 'radial-gradient(circle, #818cf8 0%, transparent 65%)' }} />

        <div className="relative z-10 max-w-4xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-2 rounded-full text-sky-300 text-[11px] font-semibold uppercase tracking-widest"
               style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.2)' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
            NextGenHacks · AI Innovation 2026
          </div>

          <h1 className="text-white font-black leading-[1.0] mb-6"
              style={{ fontSize: 'clamp(3rem, 7vw, 6rem)', letterSpacing: '-0.03em' }}>
            Predict.<br />
            <span className="text-sky-400">Personalise.</span><br />
            Retain.
          </h1>

          <p className="text-white/55 text-[17px] leading-relaxed mb-10 max-w-2xl mx-auto">
            A fully agentic 7-layer AI/ML platform that identifies retail banking customers
            at risk of attrition <strong className="text-white/80">weeks before any explicit signal</strong> — and
            automatically orchestrates hyper-personalised outreach.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link href="/login"
              className="inline-flex items-center gap-2 text-[15px] font-bold px-8 py-4 rounded-xl text-white transition-all hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, #1d4ed8, #0f2d5c)', boxShadow: '0 8px 32px rgba(29,78,216,0.4)' }}>
              Try the Demo <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="#architecture"
              className="inline-flex items-center gap-2 text-[14px] font-semibold px-6 py-4 rounded-xl text-white/60 hover:text-white transition-colors"
              style={{ border: '1px solid rgba(255,255,255,0.12)' }}>
              See Architecture
            </a>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-4 gap-4 mt-20 max-w-2xl mx-auto">
            {[
              { v: '50',    l: 'Customers' },
              { v: '0.93',  l: 'AUC Score' },
              { v: '9',     l: 'Signal Streams' },
              { v: '< 4h',  l: 'Detection Lag' },
            ].map(s => (
              <div key={s.l} className="text-center p-4 rounded-xl"
                   style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <p className="text-white text-[24px] font-black leading-none">{s.v}</p>
                <p className="text-white/35 text-[10px] uppercase tracking-wider mt-1.5">{s.l}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-white/25 animate-bounce">
          <span className="text-[10px] uppercase tracking-widest">Scroll</span>
          <ChevronDown className="w-4 h-4" />
        </div>
      </section>

      {/* ── DEMO DISCLAIMER ─────────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-amber-50 border-y border-amber-200">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-start gap-5 mb-10">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 border border-amber-200 flex items-center justify-center shrink-0">
              <Shield className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="text-[22px] font-black text-amber-900 mb-2">Demonstration Environment</h2>
              <p className="text-[14px] text-amber-700 leading-relaxed max-w-3xl">
                This is a <strong>functional prototype</strong> built to show exactly how PCOP looks and behaves in a real-world deployment.
                The UI, dashboards, signals, scores, and AI-generated content are all representative of real system output —
                but customer data is synthetic and pre-computed offline.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {REAL.map((r, i) => (
              <div key={i} className={`flex items-start gap-3 p-4 rounded-xl border ${r.real ? 'bg-green-50 border-green-200' : 'bg-white border-slate-200'}`}>
                {r.real
                  ? <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                  : <AlertCircle  className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />}
                <p className={`text-[13px] leading-snug ${r.real ? 'text-green-800' : 'text-slate-600'}`}>{r.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-[11px] font-semibold text-sky-600 uppercase tracking-widest mb-3">ARGUS · Layer 2</p>
            <h2 className="text-[32px] font-black text-slate-900 mb-3" style={{ letterSpacing: '-0.02em' }}>What Signals Look Like in Production</h2>
            <p className="text-slate-400 text-[15px] max-w-xl mx-auto">9 behavioural streams per customer, 3 statistical methods. These would fire on real transaction data.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {SIGNALS.map(s => (
              <div key={s.type} className="p-5 rounded-2xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all group">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[14px] font-bold text-slate-800">{s.type}</p>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-wide ${METHOD[s.method]}`}>{s.method}</span>
                    <span className="text-[12px] font-black text-slate-700">{s.conf}%</span>
                  </div>
                </div>
                <p className="text-[12px] text-slate-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 p-4 rounded-xl bg-slate-50 border border-slate-200 text-center">
            <p className="text-[12px] text-slate-500">
              <strong className="text-slate-700">SR</strong> — Shiryaev-Roberts (gradual regime shifts) ·{' '}
              <strong className="text-slate-700">CUSUM</strong> — Two-sided cumulative sum (step changes) ·{' '}
              <strong className="text-slate-700">SPRT</strong> — Wald sequential probability ratio test (rates)
            </p>
          </div>
        </div>
      </section>

      {/* ── ARCHITECTURE ────────────────────────────────────────────────── */}
      <section id="architecture" className="py-24 px-6"
               style={{ background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)' }}>
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-3">System Design</p>
            <h2 className="text-[32px] font-black text-slate-900 mb-3" style={{ letterSpacing: '-0.02em' }}>Seven-Layer Architecture</h2>
            <p className="text-slate-400 text-[14px]">Data flows top-to-bottom. Learning flows bottom-to-top.</p>
          </div>

          <div className="space-y-2">
            {LAYERS.map((layer, i) => (
              <div key={layer.id} className="flex rounded-xl overflow-hidden border border-slate-200 bg-white shadow-sm hover:shadow-md transition-all group">
                <div className="w-[96px] shrink-0 flex flex-col items-center justify-center py-4 text-white"
                     style={{ backgroundColor: layer.color }}>
                  <span className="text-[9px] font-bold opacity-60 uppercase tracking-widest">{layer.id}</span>
                  <span className="text-[13px] font-black tracking-tight mt-0.5">{layer.name}</span>
                </div>
                <div className="flex-1 px-5 py-3 flex items-center">
                  <p className="text-[12px] text-slate-500">{layer.desc}</p>
                </div>
                <div className="flex items-center pr-4">
                  <span className="w-6 h-6 rounded-full text-[10px] font-black text-white flex items-center justify-center"
                        style={{ backgroundColor: layer.color }}>{i + 1}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── API ─────────────────────────────────────────────────────────── */}
      <section id="api" className="py-24 px-6 text-white"
               style={{ background: 'linear-gradient(145deg, #06112a 0%, #0f2d5c 100%)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full text-sky-300 text-[11px] font-semibold uppercase tracking-widest"
                   style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.2)' }}>
                <Plug className="w-3.5 h-3.5" />
                API-First Design
              </div>
              <h2 className="text-[32px] font-black mb-4 leading-tight" style={{ letterSpacing: '-0.02em' }}>
                Plug into any banking portal
              </h2>
              <p className="text-white/55 text-[15px] leading-relaxed mb-6">
                PCOP ships as a REST API. The dashboard you're about to explore is just one possible interface —
                any CRM, relationship manager tool, or internal portal can query the same endpoints.
              </p>
              <div className="space-y-3">
                {[
                  { label: 'Full customer snapshot', sub: 'Score + signals + plan + outreach in one call' },
                  { label: 'Live AI content generation', sub: 'HERALD writes email/SMS/push via DeepSeek in <3s' },
                  { label: 'Portfolio-level KPIs',  sub: 'Dashboard-ready aggregates and tier distributions' },
                ].map(f => (
                  <div key={f.label} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full bg-sky-400/20 border border-sky-400/30 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    </div>
                    <div>
                      <p className="text-[13px] font-semibold text-white">{f.label}</p>
                      <p className="text-[12px] text-white/40">{f.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/8">
                <Code2 className="w-3.5 h-3.5 text-white/30" />
                <span className="text-[11px] font-semibold text-white/30 uppercase tracking-widest">Available Endpoints</span>
              </div>
              {[
                { m: 'GET',  p: '/api/customers',         d: 'List with risk scores & filters' },
                { m: 'GET',  p: '/api/customers/:id',     d: 'Full snapshot in one response' },
                { m: 'GET',  p: '/api/v2/signals',        d: 'All active ARGUS alarms' },
                { m: 'POST', p: '/api/outreach/generate', d: 'Live HERALD content via DeepSeek' },
                { m: 'POST', p: '/api/analysis/analyze',  d: 'AI risk analysis for customer' },
                { m: 'GET',  p: '/api/portfolio/full',    d: 'Executive dashboard data' },
                { m: 'GET',  p: '/api/kafka/stream',      d: 'SSE live event stream' },
              ].map(e => (
                <div key={e.p} className="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 last:border-0">
                  <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase shrink-0 ${e.m === 'GET' ? 'bg-green-400/15 text-green-400' : 'bg-blue-400/15 text-blue-400'}`}>{e.m}</span>
                  <code className="text-[11px] font-mono text-sky-300 shrink-0">{e.p}</code>
                  <span className="text-[10px] text-white/30 min-w-0 truncate">{e.d}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── LOGIN / CREDENTIALS ─────────────────────────────────────────── */}
      <section id="login" className="py-24 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-3">No sign-up required</p>
            <h2 className="text-[32px] font-black text-slate-900 mb-3" style={{ letterSpacing: '-0.02em' }}>Log in and explore</h2>
            <p className="text-slate-400 text-[15px]">Three role levels to explore different parts of the platform.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-4 mb-10">
            {CREDS.map(c => (
              <div key={c.user} className="rounded-2xl border border-slate-200 p-6 hover:border-[#0f2d5c]/30 hover:shadow-md transition-all">
                <div className="w-10 h-10 rounded-xl bg-[#0f2d5c] flex items-center justify-center mb-4">
                  <span className="text-white text-[11px] font-black">
                    {c.role.split(' ').map(w=>w[0]).join('').slice(0,2)}
                  </span>
                </div>
                <p className="text-[15px] font-bold text-slate-900 mb-1">{c.role}</p>
                <p className="text-[12px] text-slate-400 mb-4">{c.access}</p>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider">Username</span>
                    <code className="text-[12px] font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">{c.user}</code>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider">Password</span>
                    <code className="text-[12px] font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">{c.pass}</code>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center">
            <Link href="/login"
              className="inline-flex items-center gap-2.5 text-[15px] font-bold px-10 py-4 rounded-xl text-white transition-all hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, #0f2d5c 0%, #1d4ed8 100%)', boxShadow: '0 8px 32px rgba(15,45,92,0.25)' }}>
              Enter the Platform <ArrowRight className="w-4 h-4" />
            </Link>
            <p className="mt-4 text-[12px] text-slate-400">Log in as <strong className="text-slate-600">admin</strong> to access everything including the review queue</p>
          </div>
        </div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="py-8 px-6 border-t border-slate-100 bg-slate-50">
        <div className="max-w-5xl mx-auto flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-[#0f2d5c] flex items-center justify-center">
              <span className="text-white text-[8px] font-black">NG</span>
            </div>
            <span className="text-[12px] text-slate-500">PCOP · NextGenHacks 2026</span>
          </div>
          <span className="text-[11px] font-semibold text-amber-600 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">Demo Environment</span>
        </div>
      </footer>
    </div>
  );
}
