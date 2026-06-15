'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, api } from '@/lib/api';
import { UpliftStats, BanditState } from '@/types';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';

export default function AnalyticsPage() {
  const router  = useRouter();
  const [uplift,  setUplift]  = useState<UpliftStats | null>(null);
  const [bandit,  setBandit]  = useState<BanditState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    Promise.all([api.getUpliftStats(), api.getBanditState()])
      .then(([uRes, bRes]) => { setUplift(uRes.data); setBandit(bRes.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  const ARM_COLORS = ['#0f2d5c','#2563eb','#7c3aed','#059669','#dc2626'];

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-[22px] font-black text-slate-900">Analytics — VERDICT &amp; ORACLE</h1>
        <p className="text-[13px] text-slate-400 mt-0.5">Causal uplift measurement · channel optimisation · continuous learning</p>
      </div>

      {loading ? (
        <div className="space-y-4">{Array.from({length:4}).map((_,i)=><Skeleton key={i} className="h-48 rounded-xl"/>)}</div>
      ) : (
        <>
          {/* ── VERDICT ──────────────────────────────────────────────────── */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-1 h-5 rounded bg-[#059669]" />
              <h2 className="text-[16px] font-black text-slate-800">L6 · VERDICT — Causal Uplift Measurement</h2>
            </div>

            {uplift && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                  {[
                    { label: 'DR-ATE', value: `+${(uplift.ate_doubly_robust*100).toFixed(2)} pp`, sub: 'doubly-robust estimate', color: '#059669' },
                    { label: '90% CI', value: `[${(uplift.ate_ci_lower*100).toFixed(2)}, ${(uplift.ate_ci_upper*100).toFixed(2)}]`, sub: 'bootstrap CI', color: '#0891b2' },
                    { label: 'Qini Coeff', value: uplift.qini_coefficient.toFixed(4), sub: 'uplift concentration', color: '#0f2d5c' },
                    { label: 'Treated', value: `${(uplift.treated_visit_rate*100).toFixed(1)}%`, sub: `${uplift.n_treated} customers`, color: '#7c3aed' },
                    { label: 'Control', value: `${(uplift.control_visit_rate*100).toFixed(1)}%`, sub: `${uplift.n_control} customers`, color: '#64748b' },
                  ].map(({label,value,sub,color}) => (
                    <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
                      <p className="text-lg font-black tabular-nums" style={{color}}>{value}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                    <h3 className="text-[13px] font-bold text-slate-800 mb-1">Qini Uplift Curve</h3>
                    <p className="text-[11px] text-slate-400 mb-4">Cumulative uplift vs random targeting · higher = better model discrimination</p>
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={uplift.qini_curve} margin={{top:4,right:4,left:-20,bottom:0}}>
                        <defs>
                          <linearGradient id="qiniGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%"   stopColor="#059669" stopOpacity={0.15}/>
                            <stop offset="100%" stopColor="#059669" stopOpacity={0.01}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis dataKey="pct" tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                        <YAxis tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                        <Tooltip formatter={(v:number)=>[v.toFixed(4),'Uplift']} contentStyle={{fontSize:11,borderRadius:8,border:'1px solid #e2e8f0'}} labelFormatter={v=>`Top ${(Number(v)*100).toFixed(0)}%`} />
                        <Area type="monotone" dataKey="uplift" stroke="#059669" strokeWidth={2.5} fill="url(#qiniGrad)" dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                    <h3 className="text-[13px] font-bold text-slate-800 mb-1">Treated vs Control</h3>
                    <p className="text-[11px] text-slate-400 mb-4">Visit rate comparison · doubly-robust ATE isolates treatment effect from selection bias</p>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={[
                        {group:'Control',  rate: uplift.control_visit_rate*100,  n: uplift.n_control},
                        {group:'Treated',  rate: uplift.treated_visit_rate*100,  n: uplift.n_treated},
                      ]} margin={{top:4,right:4,left:-10,bottom:0}}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis dataKey="group" tick={{fontSize:11,fill:'#64748b'}} axisLine={false} tickLine={false} />
                        <YAxis tickFormatter={v=>`${v.toFixed(0)}%`} tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                        <Tooltip formatter={(v:number)=>[`${v.toFixed(1)}%`,'Visit Rate']} contentStyle={{fontSize:11,borderRadius:8}} />
                        <Bar dataKey="rate" fill="#64748b" radius={[4,4,0,0]} maxBarSize={60} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="mt-3 text-[12px] text-slate-600 text-center">
                      Uplift = <strong className="text-[#059669]">+{((uplift.treated_visit_rate-uplift.control_visit_rate)*100).toFixed(1)} pp</strong> visit rate lift from email campaign
                    </p>
                  </div>
                </div>
              </>
            )}
          </section>

          {/* ── ORACLE ───────────────────────────────────────────────────── */}
          {bandit && (
            <section>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-1 h-5 rounded bg-[#d97706]" />
                <h2 className="text-[16px] font-black text-slate-800">L7 · ORACLE — Thompson Sampling Channel Bandit</h2>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                {/* Arm cards */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                  <h3 className="text-[13px] font-bold text-slate-800 mb-4">
                    Channel Arm Performance
                    <span className="ml-2 text-[11px] font-normal text-slate-400">{bandit.total_steps.toLocaleString()} rounds · best: <strong className="text-[#0f2d5c]">{bandit.best_arm}</strong></span>
                  </h3>
                  <div className="space-y-3">
                    {bandit.arms.map((arm, i) => {
                      const er    = bandit.expected_reward[i];
                      const sel   = bandit.selection_counts[i];
                      const isBest= arm === bandit.best_arm;
                      return (
                        <div key={arm}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[12px] font-semibold text-slate-700">{arm}</span>
                              {isBest && <span className="text-[9px] bg-[#0f2d5c] text-white px-1.5 py-0.5 rounded-full font-bold">BEST</span>}
                            </div>
                            <div className="flex items-center gap-3 text-[11px]">
                              <span className="font-bold" style={{color: ARM_COLORS[i]}}>{(er*100).toFixed(1)}%</span>
                              <span className="text-slate-400">{sel} selected</span>
                            </div>
                          </div>
                          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all" style={{width:`${er*100/0.35}%`, backgroundColor: ARM_COLORS[i]}} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <p className="text-[12px] text-slate-600">
                      Regret reduction: <strong className="text-[#059669]">{bandit.regret_reduction_pct.toFixed(1)}%</strong> vs random policy
                    </p>
                  </div>
                </div>

                {/* Posterior distributions */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                  <h3 className="text-[13px] font-bold text-slate-800 mb-1">Beta Posterior Distributions</h3>
                  <p className="text-[11px] text-slate-400 mb-4">Each arm's Beta(α,β) posterior · width = uncertainty · mean = expected reward</p>
                  <div className="space-y-2">
                    {bandit.posteriors.map((p, i) => (
                      <div key={p.arm} className="flex items-center gap-3 text-[11px]">
                        <span className="w-16 text-slate-600 shrink-0">{p.arm}</span>
                        <div className="flex-1 h-4 bg-slate-100 rounded-full overflow-hidden relative">
                          <div className="absolute inset-y-0 left-0 rounded-full opacity-80"
                            style={{width:`${p.mean*100/0.4}%`, backgroundColor: ARM_COLORS[i]}} />
                        </div>
                        <div className="text-slate-500 w-32 text-right shrink-0">
                          β({p.alpha},{p.beta}) = {(p.mean*100).toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <p className="text-[11px] text-slate-500">
                      <strong>Thompson Sampling:</strong> each round, sample θ_i ~ Beta(α_i, β_i) for each arm.
                      Select arm = argmax(θ). On reward: α += 1. On no reward: β += 1.
                      No ε-greedy hyperparameter needed — exploration is automatic.
                    </p>
                  </div>
                </div>
              </div>

              {/* Prompt performance */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h3 className="text-[13px] font-bold text-slate-800 mb-4">HERALD Prompt Variant Performance (REFINE cycle)</h3>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { name: 'Offer-Lead',   open: 22, ctr: 11, conv: 6.0, color: '#0f2d5c' },
                    { name: 'Empathy-Lead', open: 28, ctr: 14, conv: 8.0, color: '#059669', winner: true },
                    { name: 'Urgency-Lead', open: 19, ctr: 9,  conv: 5.0, color: '#dc2626' },
                  ].map(v => (
                    <div key={v.name} className={`rounded-xl border p-4 ${v.winner ? 'border-green-300 bg-green-50' : 'border-slate-200 bg-white'}`}>
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-[13px] font-bold text-slate-800">{v.name}</p>
                        {v.winner && <span className="text-[9px] bg-green-600 text-white px-1.5 py-0.5 rounded-full font-bold">WINNER</span>}
                      </div>
                      {[
                        { label: 'Open Rate',  value: v.open, color: v.color },
                        { label: 'CTR',        value: v.ctr,  color: v.color },
                        { label: 'Conversion', value: v.conv, color: v.color },
                      ].map(m => (
                        <div key={m.label} className="mb-2">
                          <div className="flex justify-between text-[10px] mb-0.5">
                            <span className="text-slate-500">{m.label}</span>
                            <span className="font-bold text-slate-800">{m.value}%</span>
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full">
                            <div className="h-full rounded-full" style={{width:`${m.value}%`, backgroundColor:m.color}} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
