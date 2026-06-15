'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, api } from '@/lib/api';
import KafkaFeed from '@/components/KafkaFeed';
import { Skeleton } from '@/components/ui/skeleton';
import { KafkaStatus } from '@/types';
import { Zap, Database, Activity } from 'lucide-react';

const TOPICS = [
  { topic: 'cbs.transactions',       desc: 'Core Banking payment events',      color: 'bg-blue-100 text-blue-700'   },
  { topic: 'cbs.account_updates',    desc: 'Balance & account changes',         color: 'bg-slate-100 text-slate-600' },
  { topic: 'crm.customer_events',    desc: 'CRM complaints & notes',            color: 'bg-purple-100 text-purple-700'},
  { topic: 'risk.signal_detections', desc: 'ARGUS-generated risk signals',      color: 'bg-red-100 text-red-700'     },
  { topic: 'risk.score_updates',     desc: 'ML score refreshes from FusionXV2', color: 'bg-orange-100 text-orange-700'},
  { topic: 'engagement.activity',    desc: 'Digital channel engagement events', color: 'bg-green-100 text-green-700' },
];

export default function PipelinePage() {
  const router = useRouter();
  const [status, setStatus] = useState<KafkaStatus | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return; }
    api.getKafkaStatus().then(r => setStatus(r.data)).catch(() => {});
    const interval = setInterval(() => {
      api.getKafkaStatus().then(r => setStatus(r.data)).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [router]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[22px] font-black text-slate-900">Data Pipeline</h1>
        <p className="text-[13px] text-slate-400 mt-0.5">Kafka stream inspector · live event feed · 6 topics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${status?.mode==='kafka'?'bg-green-100':'bg-amber-100'}`}>
            <Zap className={`w-4 h-4 ${status?.mode==='kafka'?'text-green-600':'text-amber-600'}`} />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Mode</p>
            <p className="text-[16px] font-black text-slate-900 capitalize">{status?.mode || 'loading'}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center">
            <Database className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Events Processed</p>
            <p className="text-[16px] font-black text-slate-900">{status?.messagesProcessed?.toLocaleString() || '0'}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#0f2d5c]/8 flex items-center justify-center">
            <Activity className="w-4 h-4 text-[#0f2d5c]" />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Last Event</p>
            <p className="text-[13px] font-bold text-slate-900">
              {status?.lastEventAt ? new Date(status.lastEventAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Topic list */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="text-[14px] font-bold text-slate-800 mb-4">Subscribed Topics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {TOPICS.map(t => (
            <div key={t.topic} className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50">
              <span className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide mt-0.5 ${t.color}`}>
                {t.topic.split('.')[0]}
              </span>
              <div>
                <p className="text-[11px] font-semibold text-slate-700 font-mono">{t.topic}</p>
                <p className="text-[10px] text-slate-400">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>
        {status?.mode === 'simulation' && (
          <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
            <p className="text-[12px] text-amber-700">
              <strong>Simulation mode:</strong> No Kafka broker detected.
              Generating realistic banking events every 8 seconds as a stand-in.
              Deploy with <code className="font-mono bg-amber-100 px-1 rounded">KAFKA_BROKERS</code> to connect to a real cluster.
            </p>
          </div>
        )}
      </div>

      {/* Live feed */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="text-[14px] font-bold text-slate-800 mb-4">Live Event Stream (SSE)</h2>
        <div className="h-96">
          <KafkaFeed maxEvents={40} />
        </div>
      </div>
    </div>
  );
}
