'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, api } from '@/lib/api';
import { Campaign, OutreachRecord, RiskTier } from '@/types';
import RiskBadge from '@/components/RiskBadge';
import { Skeleton } from '@/components/ui/skeleton';
import { Mail, MessageSquare, Bell, Phone, Users, TrendingUp, Send } from 'lucide-react';

const CHANNEL_ICONS: Record<string, React.ElementType> = {
  email: Mail, sms: MessageSquare, push: Bell, phone: Phone,
};

const STATUS_STYLES: Record<string, string> = {
  sent:      'bg-slate-100 text-slate-600',
  delivered: 'bg-blue-100 text-blue-700',
  opened:    'bg-amber-100 text-amber-700',
  clicked:   'bg-green-100 text-green-700',
  failed:    'bg-red-100 text-red-700',
};

export default function OutreachPage() {
  const router  = useRouter();
  const [campaigns,   setCampaigns]  = useState<Campaign[]>([]);
  const [records,     setRecords]    = useState<OutreachRecord[]>([]);
  const [selected,    setSelected]   = useState<OutreachRecord | null>(null);
  const [loading,     setLoading]    = useState(true);
  const [filterChan,  setFilterChan] = useState('');
  const [filterStatus,setFilterStatus]=useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    Promise.all([api.getCampaigns(), api.getOutreach({ limit: 100 })])
      .then(([cRes, oRes]) => {
        setCampaigns(cRes.campaigns || []);
        setRecords(oRes.records || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  const filtered = records.filter(r =>
    (!filterChan   || r.channel === filterChan) &&
    (!filterStatus || r.status  === filterStatus)
  );

  const stats = {
    sent:       records.length,
    opened:     records.filter(r=>['opened','clicked'].includes(r.status)).length,
    clicked:    records.filter(r=>r.status==='clicked').length,
    open_rate:  records.length ? (records.filter(r=>['opened','clicked'].includes(r.status)).length / records.length * 100).toFixed(1) : '0',
    click_rate: records.length ? (records.filter(r=>r.status==='clicked').length / records.length * 100).toFixed(1) : '0',
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[22px] font-black text-slate-900">HERALD Outreach Hub</h1>
        <p className="text-[13px] text-slate-400 mt-0.5">Hyper-personalised content generation · campaigns · dispatch status</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Dispatched', value: stats.sent,       icon: Send },
          { label: 'Opened',           value: stats.opened,     icon: Mail },
          { label: 'Open Rate',        value: `${stats.open_rate}%`, icon: TrendingUp },
          { label: 'Click Rate',       value: `${stats.click_rate}%`, icon: Users },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#0f2d5c]/8 flex items-center justify-center shrink-0">
              <Icon className="w-4 h-4 text-[#0f2d5c]" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
              <p className="text-xl font-black text-slate-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {loading ? <Skeleton className="h-48 rounded-xl" /> : (
        <>
          {/* Campaign cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {campaigns.map(c => {
              const ChannelIcon = CHANNEL_ICONS[c.channel] || Mail;
              const conversion  = c.customers > 0 ? ((c.conversions/c.customers)*100).toFixed(1) : '0';
              return (
                <div key={c.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-[14px] font-bold text-slate-800">{c.name}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <ChannelIcon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="text-[11px] text-slate-400 capitalize">{c.channel}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      c.status==='active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {c.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-slate-50 rounded-lg p-2">
                      <p className="text-[16px] font-black text-slate-800">{c.customers}</p>
                      <p className="text-[9px] text-slate-400">customers</p>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2">
                      <p className="text-[16px] font-black text-slate-800">{c.opens}</p>
                      <p className="text-[9px] text-slate-400">opens</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-2">
                      <p className="text-[16px] font-black text-green-700">{conversion}%</p>
                      <p className="text-[9px] text-green-500">conv.</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Filters + records table */}
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              {/* Filters */}
              <div className="flex gap-3 p-4 border-b border-slate-100 bg-slate-50">
                <select value={filterChan} onChange={e=>setFilterChan(e.target.value)}
                  className="px-3 py-1.5 text-[12px] rounded-lg border border-slate-200 bg-white text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#0f2d5c]/20">
                  <option value="">All Channels</option>
                  {['email','sms','push','phone'].map(c=><option key={c} value={c}>{c}</option>)}
                </select>
                <select value={filterStatus} onChange={e=>setFilterStatus(e.target.value)}
                  className="px-3 py-1.5 text-[12px] rounded-lg border border-slate-200 bg-white text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#0f2d5c]/20">
                  <option value="">All Statuses</option>
                  {['sent','delivered','opened','clicked','failed'].map(s=><option key={s} value={s}>{s}</option>)}
                </select>
                <span className="text-[12px] text-slate-400 self-center">{filtered.length} records</span>
              </div>

              {/* Table */}
              <div className="overflow-y-auto max-h-[500px]">
                <table className="w-full text-[12px]">
                  <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
                    <tr className="text-[10px] text-slate-400 uppercase tracking-wider">
                      {['Customer','Channel','Status','Offer','Dispatched'].map(h=>(
                        <th key={h} className="text-left py-2.5 px-4 font-semibold">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(r => {
                      const ChIcon = CHANNEL_ICONS[r.channel] || Mail;
                      return (
                        <tr key={r.id}
                          onClick={() => setSelected(r === selected ? null : r)}
                          className={`border-b border-slate-100 cursor-pointer transition-colors ${r===selected?'bg-slate-50':'hover:bg-slate-50'}`}>
                          <td className="py-2 px-4 font-semibold text-slate-800">{r.customer_id}</td>
                          <td className="py-2 px-4">
                            <span className="flex items-center gap-1.5 text-slate-500">
                              <ChIcon className="w-3.5 h-3.5" />
                              {r.channel}
                            </span>
                          </td>
                          <td className="py-2 px-4">
                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${STATUS_STYLES[r.status]||'bg-slate-100 text-slate-600'}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2 px-4 text-slate-500">{r.offer_code.replace(/_/g,' ')}</td>
                          <td className="py-2 px-4 text-slate-400">{new Date(r.dispatched_at).toLocaleDateString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Content preview panel */}
            {selected && (
              <div className="w-full lg:w-80 bg-white rounded-xl border border-slate-200 shadow-sm p-5 shrink-0">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[13px] font-bold text-slate-800">Content Preview</p>
                  <button onClick={()=>setSelected(null)} className="text-slate-400 hover:text-slate-600 text-[18px] leading-none">×</button>
                </div>
                <p className="text-[11px] text-slate-500 mb-3">{selected.customer_id} · {selected.channel} · {selected.status}</p>
                <div className="bg-slate-50 rounded-lg border border-slate-200 p-3">
                  <p className="text-[12px] text-slate-600 leading-relaxed">{selected.content_preview}</p>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
