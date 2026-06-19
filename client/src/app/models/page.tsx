'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, api } from '@/lib/api';
import { ModelHealth } from '@/types';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { BrainCircuit, TrendingUp, Target, Layers } from 'lucide-react';

const MODELS = [
  {
    key:    'genesis',
    name:   'GENESIS',
    full:   'Logistic Regression Cold-Start',
    desc:   'Cold-start scorer for customers with < 90 days tenure or < 30 transaction tokens. 7 onboarding features, L2-regularised LR, Platt scaling.',
    color:  '#6366f1',
  },
  {
    key:    'habitat',
    name:   'HABITAT',
    full:   'XGBoost Tabular Scorer (Pass 1)',
    desc:   '14 behavioural features: recency, frequency, monetary, complaints, digital ratio, tenure. 300–400 rounds, focal loss for class imbalance.',
    color:  '#0891b2',
  },
  {
    key:    'tare',
    name:   'TARE',
    full:   'Temporal Transformer Encoder',
    desc:   '2-layer Transformer (4 heads, d_model=128) on 180-token transaction sequences. Detects rhythm changes: weekend-only usage, late-night decline.',
    color:  '#7c3aed',
  },
  {
    key:    'graph_sage',
    name:   'GraphSAGE',
    full:   'Customer Knowledge Graph GNN',
    desc:   '2-layer GraphSAGE on k-NN customer graph (k=15, cosine similarity). Captures peer-network churn contagion invisible to tabular models.',
    color:  '#059669',
  },
];

export default function ModelsPage() {
  const router  = useRouter();
  const [health, setHealth] = useState<ModelHealth | null>(null);
  const [loading,setLoading]= useState(true);

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    api.getModelHealth()
      .then(r => setHealth(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  const FUSION_PIE = health ? MODELS.map(m => ({
    name:  m.name,
    value: (health.ensemble_weights[m.key] || 0) * 100,
    color: m.color,
  })) : [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-black text-slate-900">CHRONOS Model Intelligence</h1>
        <p className="text-[13px] text-slate-400 mt-0.5">
          {health ? `5-model ensemble · last retrained ${health.last_retrained} · ${health.n_customers_scored} customers scored` : 'Loading…'}
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4">{Array.from({length:6}).map((_,i)=><Skeleton key={i} className="h-40 rounded-xl"/>)}</div>
      ) : health && (
        <>
          {/* Summary stat row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: BrainCircuit, label: 'Fusion AUC',      value: health.fusion_auc.toFixed(3),  color: '#0f2d5c' },
              { icon: Target,       label: 'ECE (calibration)',value: health.fusion_ece.toFixed(4),  color: health.fusion_ece<0.05?'#16a34a':'#ea580c' },
              { icon: TrendingUp,   label: 'GraphSAGE AUC',   value: (health.model_aucs.graph_sage||0).toFixed(3), color: '#059669' },
              { icon: Layers,       label: 'Models',           value: '5',                           color: '#7c3aed' },
            ].map(({icon:Icon,label,value,color}) => (
              <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{backgroundColor:`${color}12`}}>
                  <Icon className="w-4.5 h-4.5" style={{color}} />
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
                  <p className="text-xl font-black text-slate-900">{value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Model cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {MODELS.map(m => {
              const auc    = health.model_aucs[m.key] || 0;
              const weight = (health.ensemble_weights[m.key] || 0) * 100;
              return (
                <div key={m.key} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-[15px] font-black text-slate-900">{m.name}</p>
                      <p className="text-[10px] text-slate-400">{m.full}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-[18px] font-black tabular-nums" style={{color: m.color}}>
                        {weight.toFixed(0)}%
                      </div>
                      <div className="text-[9px] text-slate-400">weight</div>
                    </div>
                  </div>
                  <div className="mb-3">
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-slate-400">AUC</span>
                      <span className="font-bold text-slate-800">{auc.toFixed(3)}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{width:`${auc*100}%`, backgroundColor: m.color}} />
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{m.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Calibration curve */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h2 className="text-[14px] font-bold text-slate-800 mb-1">Calibration Curve</h2>
              <h2 className="text-[14px] font-bold text-slate-800 mb-1">Ensemble Weights</h2>
              <p className="text-[11px] text-slate-400 mb-3">Brier-score-derived fusion weights</p>
              <ResponsiveContainer width="100%" height={130}>
                <PieChart>
                  <Pie data={FUSION_PIE} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={3} dataKey="value" startAngle={90} endAngle={-270}>
                    {FUSION_PIE.map(d => <Cell key={d.name} fill={d.color} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`${Number(v).toFixed(0)}%`]} contentStyle={{fontSize:11,borderRadius:8}} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {FUSION_PIE.map(d => (
                  <div key={d.name} className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{backgroundColor:d.color}} />
                      <span className="text-slate-600">{d.name}</span>
                    </div>
                    <span className="font-bold text-slate-800">{d.value.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Feature importance */}
        ```tsx
<div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
  {/* Calibration curve */}
  <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
    <h2 className="text-[14px] font-bold text-slate-800 mb-1">Calibration Curve</h2>
    <p className="text-[11px] text-slate-400 mb-4">
      Predicted probability vs actual churn rate per bin · ECE={health.fusion_ece.toFixed(4)}
    </p>

    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={health.calibration_points} margin={{top:4,right:4,left:-20,bottom:0}}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="predicted" tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
        <Tooltip formatter={(v)=>[`${(Number(v)*100).toFixed(1)}%`]} contentStyle={{fontSize:11,borderRadius:8,border:'1px solid #e2e8f0'}} />
        <Line type="linear" dataKey="predicted" stroke="#cbd5e1" strokeWidth={1.5} strokeDasharray="4 3" dot={false} />
        <Line type="monotone" dataKey="actual" stroke="#0f2d5c" strokeWidth={2.5} dot={{r:4,fill:'#0f2d5c'}} />
        <Legend wrapperStyle={{fontSize:11}} />
      </LineChart>
    </ResponsiveContainer>
  </div>

  {/* Ensemble weights */}
  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
    <h2 className="text-[14px] font-bold text-slate-800 mb-1">Ensemble Weights</h2>
    <p className="text-[11px] text-slate-400 mb-3">Brier-score-derived fusion weights</p>

    <ResponsiveContainer width="100%" height={130}>
      <PieChart>
        <Pie data={FUSION_PIE} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={3} dataKey="value" startAngle={90} endAngle={-270}>
          {FUSION_PIE.map(d => <Cell key={d.name} fill={d.color} />)}
        </Pie>
        <Tooltip formatter={(v)=>[`${Number(v).toFixed(0)}%`]} contentStyle={{fontSize:11,borderRadius:8}} />
      </PieChart>
    </ResponsiveContainer>

    <div className="space-y-1.5 mt-2">
      {FUSION_PIE.map(d => (
        <div key={d.name} className="flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{backgroundColor:d.color}} />
            <span className="text-slate-600">{d.name}</span>
          </div>
          <span className="font-bold text-slate-800">{d.value.toFixed(0)}%</span>
        </div>
      ))}
    </div>
  </div>
</div>
```
