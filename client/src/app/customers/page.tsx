'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, api } from '@/lib/api';
import { Customer, RiskTier } from '@/types';
import RiskBadge, { tierColor } from '@/components/RiskBadge';
import ScoreBar from '@/components/ScoreBar';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, LayoutGrid, List, ArrowUpDown, ChevronUp, ChevronDown } from 'lucide-react';

const SEGMENTS   = ['All Segments', 'HNW', 'Mass Affluent', 'Mass Market', 'SME'];
const TIERS      = ['All Tiers', 'PRIORITY', 'ESCALATE', 'STANDARD', 'MONITOR', 'NONE'];
const ARCHETYPES = ['All Archetypes', 'vip_loyal', 'healthy_active', 'drifting', 'high_risk', 'critical'];
const SORT_OPTS  = [
  { label: 'Score ↓', value: 'score_desc' },
  { label: 'Score ↑', value: 'score_asc'  },
  { label: 'Name',    value: 'name'        },
];

const ARCHETYPE_LABELS: Record<string, string> = {
  vip_loyal:      'VIP Loyal', healthy_active: 'Healthy Active',
  drifting:       'Drifting',  high_risk:      'High Risk',
  critical:       'Critical',
};

function CustomerCard({ c }: { c: Customer }) {
  return (
    <Link href={`/customers/${c.customer_id}`}
      className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 hover:border-[#0f2d5c]/30 hover:shadow-md transition-all group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-[12px] font-bold text-slate-600">
            {c.full_name.split(' ').map(n => n[0]).join('').slice(0,2)}
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-900 group-hover:text-[#0f2d5c] leading-tight">{c.full_name}</p>
            <p className="text-[10px] text-slate-400">{c.customer_id}</p>
          </div>
        </div>
        <RiskBadge tier={c.risk_tier} size="sm" />
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-slate-400">Churn Score</span>
          <span className="text-[11px] font-bold tabular-nums" style={{color: tierColor(c.risk_tier)}}>
            {(c.churn_score * 100).toFixed(0)}%
          </span>
        </div>
        <ScoreBar score={c.churn_score} tier={c.risk_tier} height={5} />
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>{c.segment}</span>
        <span>{c.city}</span>
        <span>{c.tenure_months}mo tenure</span>
      </div>

      {c.life_event && (
        <div className="mt-2.5 px-2 py-1 rounded bg-purple-50 border border-purple-100">
          <p className="text-[10px] text-purple-700 font-medium">{c.life_event.replace(/_/g,' ')}</p>
        </div>
      )}
    </Link>
  );
}

function CustomerRow({ c }: { c: Customer }) {
  return (
    <Link href={`/customers/${c.customer_id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0 group">
      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
        {c.full_name.split(' ').map(n => n[0]).join('').slice(0,2)}
      </div>
      <div className="w-44 min-w-0">
        <p className="text-[12px] font-semibold text-slate-800 truncate group-hover:text-[#0f2d5c]">{c.full_name}</p>
        <p className="text-[10px] text-slate-400">{c.customer_id}</p>
      </div>
      <div className="w-28"><RiskBadge tier={c.risk_tier} /></div>
      <div className="w-36 flex items-center gap-2">
        <ScoreBar score={c.churn_score} tier={c.risk_tier} height={4} showLabel />
      </div>
      <div className="w-28 text-[11px] text-slate-500">{c.segment}</div>
      <div className="w-24 text-[11px] text-slate-500">{c.city}</div>
      <div className="w-20 text-[11px] text-slate-500">{c.tenure_months}mo</div>
      <div className="w-24 text-[11px] text-slate-500">{c.employer.slice(0,18)}{c.employer.length>18?'…':''}</div>
      <div className="flex-1 text-[10px] text-purple-600">{c.life_event?.replace(/_/g,' ') || ''}</div>
    </Link>
  );
}

export default function CustomersPage() {
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [total,     setTotal]     = useState(0);
  const [loading,   setLoading]   = useState(true);
  const [view,      setView]      = useState<'grid'|'list'>('grid');
  const [search,    setSearch]    = useState('');
  const [segment,   setSegment]   = useState('');
  const [tier,      setTier]      = useState('');
  const [archetype, setArchetype] = useState('');
  const [sort,      setSort]      = useState('score_desc');

  const loadCustomers = useCallback(() => {
    if (!getToken()) { router.push('/login'); return; }
    setLoading(true);
    api.getCustomers({
      search:    search    || undefined,
      segment:   segment   || undefined,
      risk_tier: tier      || undefined,
      archetype: archetype || undefined,
      sort,
      limit: 100,
    })
    .then(r => { setCustomers(r.customers); setTotal(r.total); })
    .catch(() => {})
    .finally(() => setLoading(false));
  }, [search, segment, tier, archetype, sort, router]);

  useEffect(() => {
    const t = setTimeout(loadCustomers, 250);
    return () => clearTimeout(t);
  }, [loadCustomers]);

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-black text-slate-900">Customer Intelligence</h1>
          <p className="text-[13px] text-slate-400 mt-0.5">{total} customers · sorted by {sort.replace('_',' ')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setView('grid')}
            className={`p-2 rounded-lg border transition-colors ${view==='grid' ? 'bg-[#0f2d5c] border-[#0f2d5c] text-white' : 'bg-white border-slate-200 text-slate-400 hover:text-slate-600'}`}>
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button onClick={() => setView('list')}
            className={`p-2 rounded-lg border transition-colors ${view==='list' ? 'bg-[#0f2d5c] border-[#0f2d5c] text-white' : 'bg-white border-slate-200 text-slate-400 hover:text-slate-600'}`}>
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search name, ID, employer…"
            className="w-full pl-9 pr-3 py-2 text-[13px] rounded-lg border border-slate-200 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#0f2d5c]/20 focus:border-[#0f2d5c] transition-all"
          />
        </div>
        {[
          { val: segment,   set: setSegment,   opts: SEGMENTS   },
          { val: tier,      set: setTier,      opts: TIERS      },
          { val: archetype, set: setArchetype, opts: ARCHETYPES },
        ].map(({ val, set, opts }, i) => (
          <select key={i} value={val} onChange={e => set(e.target.value.includes('All') ? '' : e.target.value)}
            className="px-3 py-2 text-[13px] rounded-lg border border-slate-200 bg-white text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#0f2d5c]/20 focus:border-[#0f2d5c]">
            {opts.map(o => <option key={o} value={o.includes('All') ? '' : o}>{o}</option>)}
          </select>
        ))}
        <select value={sort} onChange={e => setSort(e.target.value)}
          className="px-3 py-2 text-[13px] rounded-lg border border-slate-200 bg-white text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#0f2d5c]/20">
          {SORT_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Results */}
      {loading ? (
        <div className={view === 'grid' ? 'grid grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4' : 'space-y-2'}>
          {Array.from({length:12}).map((_,i) => <Skeleton key={i} className={view==='grid'?'h-40 rounded-xl':'h-14 rounded-lg'} />)}
        </div>
      ) : view === 'grid' ? (
        <div className="grid grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
          {customers.map(c => <CustomerCard key={c.customer_id} c={c} />)}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Table header */}
          <div className="flex items-center gap-3 px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            <div className="w-7" />
            <div className="w-44">Name</div>
            <div className="w-28">Risk Tier</div>
            <div className="w-36">Churn Score</div>
            <div className="w-28">Segment</div>
            <div className="w-24">City</div>
            <div className="w-20">Tenure</div>
            <div className="w-24">Employer</div>
            <div className="flex-1">Life Event</div>
          </div>
          {customers.map(c => <CustomerRow key={c.customer_id} c={c} />)}
        </div>
      )}

      {customers.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Search className="w-8 h-8 mb-3" />
          <p className="text-[14px] font-medium">No customers match your filters</p>
        </div>
      )}
    </div>
  );
}
