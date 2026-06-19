'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, api } from '@/lib/api';
import { Portfolio } from '@/types';
import RiskBadge, { tierColor } from '@/components/RiskBadge';
import ScoreBar from '@/components/ScoreBar';
import KafkaFeed from '@/components/KafkaFeed';
import { KnowledgeGraphCard } from '@/components/dashboard/KnowledgeGraphCard';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { Users, AlertTriangle, TrendingUp, Activity, Zap, Heart, ArrowUpRight } from 'lucide-react';

const TIER_COLORS = {
  PRIORITY: '#dc2626', ESCALATE: '#ea580c',
  STANDARD: '#ca8a04', MONITOR: '#2563eb', NONE: '#16a34a',
};

function KpiCard({ icon: Icon, label, value, sub, color = '#0f2d5c' }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex items-start gap-4">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${color}12` }}>
        <Icon className="w-4.5 h-4.5" style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">{label}</p>
        <p className="text-2xl font-black text-slate-900 leading-tight">{value}</p>
        {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function SectionHeader({ title, sub, href }: { title: string; sub?: string; href?: string }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h2 className="text-[15px] font-bold text-slate-800">{title}</h2>
        {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
      {href && (
        <Link href={href} className="flex items-center gap-1 text-[12px] text-[#0f2d5c] font-semibold hover:opacity-70 transition-opacity">
          View all <ArrowUpRight className="w-3 h-3" />
        </Link>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const router  = useRouter();
  const [data,  setData]    = useState<Portfolio | null>(null);
  const [error, setError]   = useState('');
  const [now,   setNow]     = useState('');

  useEffect(() => { setNow(new Date().toLocaleTimeString()); }, []);

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    api.getPortfolioFull()
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load portfolio data.'));
  }, [router]);

  if (error) return (
    <div className="p-8 flex items-center justify-center h-64 text-red-500 text-sm">{error}</div>
  );

  const s = data?.summary;

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-black text-slate-900">Executive Overview</h1>
          <p className="text-[13px] text-slate-400 mt-0.5">Portfolio risk summary · all 50 customers</p>
        </div>
        <div className="text-[11px] text-slate-400 bg-white border border-slate-200 rounded-lg px-3 py-1.5">
          Last updated: {now || '—'}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {!s ? Array.from({length:6}).map((_,i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        )) : <>
          <KpiCard icon={Users}         label="Customers"       value={s.total_customers}    color="#0f2d5c" />
          <KpiCard icon={AlertTriangle}  label="Priority"        value={s.priority_count}     color="#dc2626" sub="score > 0.80" />
          <KpiCard icon={TrendingUp}     label="Escalate"        value={s.escalate_count}     color="#ea580c" sub="score 0.60–0.80" />
          <KpiCard icon={Activity}       label="Avg Score"       value={(s.avg_churn_score*100).toFixed(1)+'%'} color="#ca8a04" />
          <KpiCard icon={Zap}            label="Active Signals"  value={s.active_signals}     color="#2563eb" />
          <KpiCard icon={Heart}          label="Life Events"     value={s.life_events_detected} color="#7c3aed" sub="detected this period" />
        </>}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Churn trend */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <SectionHeader title="Churn Score Trend" sub="12-week portfolio average" />
          {!data ? <Skeleton className="h-48" /> : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.churn_trend} margin={{top:4,right:4,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(v) => [`${(Number(v)*100).toFixed(1)}%`, 'Avg Score']}
                  contentStyle={{fontSize:11,border:'1px solid #e2e8f0',borderRadius:8,padding:'6px 10px'}}
                />
                <Line type="monotone" dataKey="avg_score" stroke="#0f2d5c" strokeWidth={2.5} dot={{r:3,fill:'#0f2d5c'}} />
                <Line type="monotone" dataKey="critical_count" stroke="#dc2626" strokeWidth={1.5} strokeDasharray="4 2" dot={false} yAxisId={undefined} hide />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Tier donut */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <SectionHeader title="Risk Tiers" sub="current distribution" />
          {!data ? <Skeleton className="h-48" /> : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={160}>
                <PieChart>
                  <Pie data={data.tier_distribution} dataKey="count" cx="50%" cy="50%" innerRadius={45} outerRadius={65} paddingAngle={2} startAngle={90} endAngle={-270}>
                    {data.tier_distribution.map((t) => (
                      <Cell key={t.tier} fill={TIER_COLORS[t.tier as keyof typeof TIER_COLORS] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v,n) => [v, n]} contentStyle={{fontSize:11,borderRadius:8}} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-1.5 flex-1">
                {data.tier_distribution.map(t => (
                  <div key={t.tier} className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{backgroundColor: TIER_COLORS[t.tier as keyof typeof TIER_COLORS]}} />
                      <span className="text-[11px] text-slate-600">{t.tier}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[12px] font-bold text-slate-800">{t.count}</span>
                      <span className="text-[10px] text-slate-400">{t.pct}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Signal breakdown + Top at risk */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Signal breakdown */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <SectionHeader title="Signal Breakdown" sub="total active alarms by type" href="/signals" />
          {!data ? <Skeleton className="h-56" /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.signal_breakdown.slice(0,9)} layout="vertical" margin={{top:0,right:10,left:60,bottom:0}}>
                <XAxis type="number" tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="type" tick={{fontSize:9.5,fill:'#64748b'}} axisLine={false} tickLine={false}
                  tickFormatter={v => v.replace(/_/g,' ')} width={60} />
                <Tooltip contentStyle={{fontSize:11,borderRadius:8,border:'1px solid #e2e8f0'}} />
                <Bar dataKey="count" fill="#0f2d5c" radius={[0,3,3,0]} maxBarSize={12} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top at risk */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <SectionHeader title="Top 10 At-Risk" sub="highest ensemble churn scores" href="/customers" />
          {!data ? (
            <div className="space-y-2">{Array.from({length:5}).map((_,i) => <Skeleton key={i} className="h-10 rounded" />)}</div>
          ) : (
            <div className="space-y-1">
              {data.top_at_risk.map((c, i) => (
                <Link key={c.customer_id} href={`/customers/${c.customer_id}`}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors group">
                  <span className="text-[11px] text-slate-300 w-4 tabular-nums">{i+1}</span>
                  <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
                    {c.full_name.split(' ').map((n:string) => n[0]).join('').slice(0,2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-semibold text-slate-800 truncate group-hover:text-[#0f2d5c]">{c.full_name}</p>
                    <p className="text-[10px] text-slate-400">{c.segment} · {c.city}</p>
                  </div>
                  <RiskBadge tier={c.risk_tier} />
                  <div className="w-20">
                    <ScoreBar score={c.churn_score} tier={c.risk_tier} height={4} showLabel />
                  </div>
                  <span className="text-[10px] text-slate-400 w-14 text-right">{c.alarm_count} signals</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Knowledge Graph */}
      <KnowledgeGraphCard />

      {/* Live Kafka feed */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <SectionHeader title="Live Event Feed" sub="real-time Kafka stream simulation" href="/pipeline" />
        <div className="h-64">
          <KafkaFeed maxEvents={25} />
        </div>
      </div>
    </div>
  );
}
