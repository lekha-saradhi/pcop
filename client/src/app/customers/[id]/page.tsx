'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, api } from '@/lib/api';
import { CustomerSnapshot, Signal, Transaction, RiskTier, HeraldContent } from '@/types';
import RiskBadge, { tierColor, tierBgColor } from '@/components/RiskBadge';
import ScoreBar from '@/components/ScoreBar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart, Bar, AreaChart, Area, ResponsiveContainer, XAxis, YAxis,
  Tooltip, CartesianGrid,
} from 'recharts';
import {
  ArrowLeft, Building2, MapPin, Clock, User, TrendingUp,
  AlertCircle, CheckCircle, Mail, MessageSquare, Bell, Phone, ChevronRight, Zap,
} from 'lucide-react';

const TABS = ['Overview','Risk Score','Signals','Transactions','Action Plan','Outreach','Survival'] as const;
type Tab = typeof TABS[number];

const METHOD_COLORS: Record<string, string> = {
  SR:    'bg-blue-100 text-blue-700',
  CUSUM: 'bg-orange-100 text-orange-700',
  SPRT:  'bg-purple-100 text-purple-700',
};

function StatBox({ label, value, sub, color }: { label:string; value:string|number; sub?:string; color?:string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-xl font-black text-slate-900" style={color ? {color} : {}}>{value}</p>
      {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function CustomerDetailPage({ params }: { params: Promise<{id:string}> }) {
  const { id }     = use(params);
  const router     = useRouter();
  const [snap,    setSnap]    = useState<CustomerSnapshot | null>(null);
  const [txns,    setTxns]    = useState<Transaction[]>([]);
  const [tab,     setTab]     = useState<Tab>('Overview');
  const [loading, setLoading] = useState(true);
  const [analysis,      setAnalysis]      = useState('');
  const [analyzing,     setAnalyzing]     = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [herald,        setHerald]        = useState<HeraldContent | null>(null);
  const [generating,    setGenerating]    = useState(false);
  const [heraldError,   setHeraldError]   = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    Promise.all([
      api.getCustomerById(id),
      api.getCustomerTransactions(id),
    ]).then(([snapRes, txnRes]) => {
      setSnap(snapRes as CustomerSnapshot);
      setTxns(txnRes.transactions || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id, router]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisError('');
    setAnalysis('');
    try {
      const r = await api.analyzeCustomer(id);
      setAnalysis(r.analysis || '');
    } catch (e: unknown) {
      setAnalysisError(e instanceof Error ? e.message : 'NVIDIA DeepSeek V4 Pro did not respond. Check the API key or network connection.');
    } finally { setAnalyzing(false); }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setHeraldError('');
    try {
      const r = await api.generateOutreach(id);
      setHerald(r.herald || null);
    } catch (e: unknown) {
      setHeraldError(e instanceof Error ? e.message : 'NVIDIA DeepSeek V4 Pro did not respond. Check the API key or network connection.');
    } finally { setGenerating(false); }
  };

  const activeHerald = herald ?? snap?.herald;

  if (loading) return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-28 rounded-xl" />
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );

  if (!snap) return (
    <div className="p-6 flex items-center gap-3 text-slate-500">
      <AlertCircle className="w-5 h-5" />
      Customer not found.
    </div>
  );

  const { customer: c, score, signals, plan, survival } = snap;

  return (
    <div className="p-6 space-y-4">
      {/* Breadcrumb */}
      <Link href="/customers" className="flex items-center gap-1.5 text-[12px] text-slate-400 hover:text-[#0f2d5c] transition-colors w-fit">
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Customers
      </Link>

      {/* Header card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full flex items-center justify-center text-[18px] font-black text-white"
              style={{ backgroundColor: tierColor(c.risk_tier) }}>
              {c.full_name.split(' ').map(n=>n[0]).join('').slice(0,2)}
            </div>
            <div>
              <h1 className="text-[20px] font-black text-slate-900">{c.full_name}</h1>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                <span className="text-[12px] text-slate-400">{c.customer_id}</span>
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                  <Building2 className="w-3 h-3" /> {c.employer}
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                  <MapPin className="w-3 h-3" /> {c.city}
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                  <Clock className="w-3 h-3" /> {c.tenure_months} months
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                  <User className="w-3 h-3" /> {c.relationship_manager}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-[10px] text-slate-400 mb-1">Ensemble Score</p>
              <p className="text-3xl font-black tabular-nums" style={{color: tierColor(c.risk_tier)}}>
                {(c.churn_score*100).toFixed(0)}%
              </p>
            </div>
            <div className="flex flex-col gap-1.5 items-end">
              <RiskBadge tier={c.risk_tier} size="md" />
              {c.life_event && (
                <span className="inline-flex items-center gap-1 text-[10px] bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full border border-purple-200">
                  {c.life_event.replace(/_/g,' ')}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2.5 text-[12px] font-semibold transition-colors ${
              tab === t
                ? 'bg-[#0f2d5c] text-white'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50 border-r border-slate-200 last:border-0'
            }`}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 min-h-[300px]">

        {/* ── Overview ─────────────────────────────────────────────────────── */}
        {tab === 'Overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-3">
              <StatBox label="Balance"      value={`₹${(c.balance/1000).toFixed(0)}K`} sub={c.segment} />
              <StatBox label="Income (ann)" value={`₹${(c.income/100000).toFixed(1)}L`} />
              <StatBox label="Inactivity"   value={`${c.inactivity_days}d`}  color={c.inactivity_days>45?'#dc2626':undefined} />
              <StatBox label="NPS Score"    value={c.nps}  color={c.nps < 3 ? '#dc2626' : c.nps > 7 ? '#16a34a' : undefined} />
              <StatBox label="Products"     value={c.product_count} />
              <StatBox label="Txn Freq 90d" value={c.txn_freq_90d} sub="transactions" />
              <StatBox label="App Logins"   value={c.app_logins_30d} sub="last 30d" />
              <StatBox label="Complaints"   value={c.complaint_count} color={c.complaint_count>2?'#dc2626':undefined} />
              <StatBox label="Digital"      value={`${(c.digital_ratio*100).toFixed(0)}%`} sub="of txns" />
              <StatBox label="Salary Credits" value={c.salary_credit_count} sub="last 3mo" />
            </div>

            {c.life_event && (
              <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
                <p className="text-[12px] font-semibold text-purple-800 mb-1">Life Event Detected: {c.life_event.replace(/_/g,' ')}</p>
                <p className="text-[12px] text-purple-600">{c.life_event_desc}</p>
              </div>
            )}

            {/* AI Analysis */}
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <p className="text-[13px] font-semibold text-slate-700">AI Risk Analysis</p>
                  <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 uppercase tracking-wide">NVIDIA DeepSeek V4 Pro</span>
                </div>
                <button onClick={handleAnalyze} disabled={analyzing}
                  className="flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1.5 rounded-lg bg-[#0f2d5c] text-white hover:bg-[#1a3f7a] disabled:opacity-50 transition-colors">
                  <TrendingUp className="w-3.5 h-3.5" />
                  {analyzing ? 'Analysing…' : analysis ? 'Regenerate' : 'Generate Analysis'}
                </button>
              </div>
              <div className="p-4">
                {analyzing ? (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2 mb-3 text-[12px] text-slate-400">
                      <div className="w-4 h-4 border-2 border-[#0f2d5c] border-t-transparent rounded-full animate-spin shrink-0" />
                      NVIDIA DeepSeek V4 Pro is analysing {c.full_name}'s risk profile…
                    </div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-slate-200 rounded-full animate-pulse" style={{width:'85%'}} /></div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-slate-200 rounded-full animate-pulse" style={{width:'65%'}} /></div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-slate-200 rounded-full animate-pulse" style={{width:'75%'}} /></div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-slate-200 rounded-full animate-pulse" style={{width:'50%'}} /></div>
                  </div>
                ) : analysisError ? (
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
                    <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-[12px] font-semibold text-red-700 mb-0.5">Analysis failed</p>
                      <p className="text-[12px] text-red-600">{analysisError}</p>
                    </div>
                  </div>
                ) : analysis ? (
                  <p className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-line">{analysis}</p>
                ) : (
                  <p className="text-[12px] text-slate-400 italic">Click "Generate Analysis" to get a live AI-powered risk assessment via NVIDIA DeepSeek V4 Pro.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Risk Score ───────────────────────────────────────────────────── */}
        {tab === 'Risk Score' && score && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatBox label="Final Score"   value={`${(score.final_score*100).toFixed(1)}%`} color={tierColor(score.risk_tier)} />
              <StatBox label="CI Lower"      value={`${(score.ci_lower*100).toFixed(1)}%`}   sub="90% conformal" />
              <StatBox label="CI Upper"      value={`${(score.ci_upper*100).toFixed(1)}%`}   sub="90% conformal" />
              <StatBox label="Disagreement"  value={`±${(score.ensemble_disagreement*100).toFixed(1)}%`} sub="model spread" />
            </div>

            <div className="space-y-3">
              <p className="text-[13px] font-semibold text-slate-700">Individual Model Scores</p>
              {[
                { name: 'GENESIS',   desc: 'LR cold-start',             score: score.genesis_score,  weight: 15 },
                { name: 'HABITAT',   desc: 'XGBoost tabular',           score: score.habitat_score,  weight: 30 },
                { name: 'TARE',      desc: 'Temporal Transformer',      score: score.tare_score,     weight: 35 },
                { name: 'GraphSAGE', desc: 'Knowledge graph GNN',       score: score.graph_score,    weight: 20 },
              ].map(m => (
                <div key={m.name} className="flex items-center gap-4">
                  <div className="w-24 shrink-0">
                    <p className="text-[12px] font-semibold text-slate-700">{m.name}</p>
                    <p className="text-[10px] text-slate-400">{m.desc}</p>
                  </div>
                  <div className="flex-1">
                    <ScoreBar score={m.score} height={8} showLabel />
                  </div>
                  <div className="text-[10px] text-slate-400 w-16 text-right">w={m.weight}%</div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'P(churn < 7d)',  val: score.p7  },
                { label: 'P(churn < 30d)', val: score.p30 },
                { label: 'P(churn < 90d)', val: score.p90 },
              ].map(({ label, val }) => (
                <div key={label} className="bg-slate-50 rounded-lg border border-slate-200 p-4 text-center">
                  <p className="text-[10px] text-slate-400 mb-1">{label}</p>
                  <p className="text-2xl font-black tabular-nums" style={{color: val>0.5?'#dc2626':val>0.25?'#ea580c':'#16a34a'}}>
                    {(val*100).toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Signals ──────────────────────────────────────────────────────── */}
        {tab === 'Signals' && (
          <div className="space-y-3">
            <p className="text-[13px] font-semibold text-slate-700 mb-4">
              {signals.length} active ARGUS signal{signals.length!==1?'s':''} detected
            </p>
            {signals.length === 0 && (
              <div className="flex items-center gap-2 text-[13px] text-slate-400">
                <CheckCircle className="w-4 h-4 text-green-500" />
                No active signals — customer profile is stable.
              </div>
            )}
            {signals.map((sig: Signal, i: number) => (
              <div key={i} className="flex items-start gap-4 p-4 rounded-lg border border-slate-200">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-[13px] font-semibold text-slate-800 capitalize">{sig.signal_type.replace(/_/g,' ')}</p>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${METHOD_COLORS[sig.method] || 'bg-slate-100 text-slate-600'}`}>
                      {sig.method}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">Active for {sig.days_active} day{sig.days_active!==1?'s':''}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[11px] text-slate-400">Confidence</p>
                  <p className="text-[16px] font-black text-slate-800">{(sig.confidence*100).toFixed(0)}%</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[11px] text-slate-400">CUSUM</p>
                  <p className="text-[16px] font-black text-orange-600">{sig.cusum_value?.toFixed(1)}</p>
                  <p className="text-[9px] text-slate-400">h={sig.alarm_threshold}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Transactions ─────────────────────────────────────────────────── */}
        {tab === 'Transactions' && (
          <div className="space-y-4">
            <p className="text-[13px] font-semibold text-slate-700">{txns.length} transactions · last 60 days</p>
            {txns.length > 0 && (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={txns.slice(-30).map(t=>({date:t.date.slice(5),amount:t.amount,type:t.type}))}
                  margin={{top:0,right:0,left:-20,bottom:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{fontSize:9,fill:'#94a3b8'}} axisLine={false} tickLine={false} interval={4} />
                  <YAxis tick={{fontSize:9,fill:'#94a3b8'}} axisLine={false} tickLine={false} tickFormatter={v=>`₹${(v/1000).toFixed(0)}K`} />
                  <Tooltip formatter={(v:number)=>[`₹${v.toLocaleString('en-IN')}`,'Amount']} contentStyle={{fontSize:11,borderRadius:8,border:'1px solid #e2e8f0'}} />
                  <Bar dataKey="amount" fill="#0f2d5c" radius={[3,3,0,0]} maxBarSize={16} />
                </BarChart>
              </ResponsiveContainer>
            )}
            <div className="overflow-y-auto max-h-72">
              <table className="w-full text-[12px]">
                <thead className="sticky top-0 bg-slate-50">
                  <tr className="border-b border-slate-200 text-[10px] text-slate-400 uppercase tracking-wider">
                    <th className="text-left py-2 px-3">Date</th>
                    <th className="text-left py-2 px-3">Type</th>
                    <th className="text-left py-2 px-3">Channel</th>
                    <th className="text-left py-2 px-3">Category</th>
                    <th className="text-right py-2 px-3">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {[...txns].reverse().map((t, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 px-3 text-slate-500">{t.date}</td>
                      <td className="py-2 px-3">
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${t.type==='CREDIT'?'bg-green-50 text-green-700':'bg-slate-100 text-slate-600'}`}>{t.type}</span>
                      </td>
                      <td className="py-2 px-3 text-slate-500">{t.channel}</td>
                      <td className="py-2 px-3 text-slate-500">{t.category}</td>
                      <td className="py-2 px-3 text-right font-semibold tabular-nums text-slate-800">₹{t.amount.toLocaleString('en-IN', {maximumFractionDigits:0})}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Action Plan ──────────────────────────────────────────────────── */}
        {tab === 'Action Plan' && plan && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatBox label="Action"    value={plan.action.replace(/_/g,' ')}   color="#0f2d5c" />
              <StatBox label="Urgency"   value={plan.urgency}                     color={plan.urgency==='IMMEDIATE'?'#dc2626':undefined} />
              <StatBox label="Offer"     value={plan.offer_display || plan.offer_code.replace(/_/g,' ')} />
              <StatBox label="Channel"   value={plan.channel} />
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Rationale</p>
              <p className="text-[13px] text-slate-700 leading-relaxed">{plan.rationale}</p>
            </div>

            {plan.life_event && (
              <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
                <p className="text-[11px] font-semibold text-purple-600 uppercase tracking-wider mb-1">Life Event Detected</p>
                <p className="text-[13px] text-purple-800">{plan.life_event.replace(/_/g,' ')}</p>
              </div>
            )}

            {plan.tone_modifiers?.length > 0 && (
              <div className="flex gap-2">
                {plan.tone_modifiers.map(t => (
                  <span key={t} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 capitalize">{t}</span>
                ))}
              </div>
            )}

            {plan.suppressed && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <p className="text-[12px] text-amber-800 font-medium">Outreach suppressed (contact fatigue / consent rules)</p>
              </div>
            )}
          </div>
        )}

        {/* ── Outreach ─────────────────────────────────────────────────────── */}
        {tab === 'Outreach' && (
          <div className="space-y-4">
            {/* Header + generate button */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[13px] font-semibold text-slate-700">HERALD Content</p>
                <p className="text-[11px] text-slate-400">
                  {herald ? 'Live — generated via NVIDIA DeepSeek V4 Pro' : activeHerald ? 'Pre-computed · click Regenerate for a live version' : 'No content yet'}
                </p>
              </div>
              <button onClick={handleGenerate} disabled={generating}
                className="flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1.5 rounded-lg bg-[#0f2d5c] text-white hover:bg-[#1a3f7a] disabled:opacity-50 transition-colors">
                <Zap className="w-3.5 h-3.5" />
                {generating ? 'Generating…' : herald ? 'Regenerate' : 'Generate with AI'}
              </button>
            </div>

            {generating ? (
              <div className="space-y-3 py-2">
                <div className="flex items-center gap-2 text-[12px] text-slate-400 mb-1">
                  <div className="w-4 h-4 border-2 border-[#0f2d5c] border-t-transparent rounded-full animate-spin shrink-0" />
                  NVIDIA DeepSeek V4 Pro is writing personalised email, SMS and push content…
                </div>
                {['Email body', 'SMS message', 'Push notification'].map(label => (
                  <div key={label} className="border border-slate-100 rounded-lg p-3 space-y-2">
                    <div className="h-2.5 w-20 bg-slate-100 rounded animate-pulse" />
                    <div className="h-2 bg-slate-100 rounded animate-pulse" />
                    <div className="h-2 bg-slate-100 rounded animate-pulse w-4/5" />
                    <div className="h-2 bg-slate-100 rounded animate-pulse w-3/5" />
                  </div>
                ))}
              </div>
            ) : heraldError ? (
              <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-[12px] font-semibold text-red-700 mb-0.5">Content generation failed</p>
                  <p className="text-[12px] text-red-600">{heraldError}</p>
                  <p className="text-[11px] text-red-400 mt-1">Check that the NVIDIA API key is set in server/.env and the endpoint is reachable.</p>
                </div>
              </div>
            ) : !activeHerald ? (
              <p className="text-[13px] text-slate-400 italic py-8 text-center">Click "Generate with AI" to produce live personalised content via NVIDIA DeepSeek V4 Pro.</p>
            ) : (
              <>
                {activeHerald.email && (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 border-b border-slate-200">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span className="text-[12px] font-semibold text-slate-700">Email</span>
                      <span className="ml-auto text-[10px] text-green-600 font-semibold bg-green-50 px-1.5 py-0.5 rounded-full">
                        {activeHerald.email.compliance_status}
                      </span>
                      <span className="text-[10px] text-slate-400">{activeHerald.email.word_count} words</span>
                    </div>
                    <div className="p-4">
                      <p className="text-[11px] font-semibold text-slate-400 mb-1">Subject</p>
                      <p className="text-[13px] font-medium text-slate-800 mb-3">{activeHerald.email.subject}</p>
                      <p className="text-[12px] text-slate-600 leading-relaxed whitespace-pre-line">{activeHerald.email.body}</p>
                    </div>
                  </div>
                )}
                {activeHerald.sms && (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 border-b border-slate-200">
                      <MessageSquare className="w-4 h-4 text-slate-400" />
                      <span className="text-[12px] font-semibold text-slate-700">SMS</span>
                      <span className="ml-auto text-[10px] text-green-600 font-semibold bg-green-50 px-1.5 py-0.5 rounded-full">
                        {activeHerald.sms.compliance_status}
                      </span>
                      <span className="text-[10px] text-slate-400">{activeHerald.sms.char_count} chars</span>
                    </div>
                    <div className="p-4">
                      <p className="text-[13px] text-slate-700 bg-slate-50 rounded-lg p-3 border border-slate-200">{activeHerald.sms.body}</p>
                    </div>
                  </div>
                )}
                {activeHerald.push && (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 border-b border-slate-200">
                      <Bell className="w-4 h-4 text-slate-400" />
                      <span className="text-[12px] font-semibold text-slate-700">Push Notification</span>
                    </div>
                    <div className="p-4 flex gap-4 items-start">
                      <div className="w-10 h-10 rounded-xl bg-[#0f2d5c] flex items-center justify-center text-white text-[10px] font-black shrink-0">UB</div>
                      <div>
                        <p className="text-[13px] font-semibold text-slate-800 mb-0.5">{activeHerald.push.title}</p>
                        <p className="text-[12px] text-slate-600">{activeHerald.push.body}</p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Survival ─────────────────────────────────────────────────────── */}
        {tab === 'Survival' && survival && (
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-4">
              {[
                { label:'P(churn < 7d)',  val: survival.p7,  color: survival.p7>0.4?'#dc2626':'#16a34a' },
                { label:'P(churn < 30d)', val: survival.p30, color: survival.p30>0.4?'#dc2626':survival.p30>0.25?'#ea580c':'#16a34a' },
                { label:'P(churn < 90d)', val: survival.p90, color: survival.p90>0.5?'#dc2626':survival.p90>0.3?'#ea580c':'#16a34a' },
              ].map(({label,val,color}) => (
                <div key={label} className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                  <p className="text-[10px] text-slate-400 mb-1">{label}</p>
                  <p className="text-2xl font-black tabular-nums" style={{color}}>{(val*100).toFixed(0)}%</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">probability</p>
                </div>
              ))}
            </div>
            <div>
              <p className="text-[13px] font-semibold text-slate-700 mb-3">DeepHit Survival Curve — P(not churned) over time</p>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart
                  data={survival.time_points.map((t:number, i:number) => ({t, s: survival.survival[i]*100}))}
                  margin={{top:4,right:8,left:-20,bottom:0}}>
                  <defs>
                    <linearGradient id="survGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor="#0f2d5c" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#0f2d5c" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="t" tick={{fontSize:10,fill:'#94a3b8'}} tickFormatter={v=>`${v}d`} axisLine={false} tickLine={false} />
                  <YAxis tick={{fontSize:10,fill:'#94a3b8'}} tickFormatter={v=>`${v.toFixed(0)}%`} axisLine={false} tickLine={false} domain={[0,100]} />
                  <Tooltip formatter={(v:number) => [`${v.toFixed(1)}%`, 'Survival']} contentStyle={{fontSize:11,borderRadius:8,border:'1px solid #e2e8f0'}} labelFormatter={v=>`Day ${v}`} />
                  <Area type="monotone" dataKey="s" stroke="#0f2d5c" strokeWidth={2.5} fill="url(#survGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
