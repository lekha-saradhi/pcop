'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, api } from '@/lib/api';
import { ReviewItem, RiskTier } from '@/types';
import RiskBadge from '@/components/RiskBadge';
import ScoreBar from '@/components/ScoreBar';
import { Skeleton } from '@/components/ui/skeleton';
import { Shield, CheckCircle, XCircle } from 'lucide-react';

export default function ReviewsPage() {
  const router = useRouter();
  const [reviews,  setReviews]  = useState<ReviewItem[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [actId,    setActId]    = useState('');
  const [notes,    setNotes]    = useState('');

  const load = () => {
    if (!getToken()) { router.push('/login'); return; }
    api.getReviews()
      .then(r => setReviews(r.reviews || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      if (action === 'approve') await api.approveReview(id, notes);
      else                       await api.rejectReview(id, notes);
      setActId(''); setNotes('');
      load();
    } catch {}
  };

  const pending   = reviews.filter(r => r.status === 'pending');
  const completed = reviews.filter(r => r.status !== 'pending');

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="w-6 h-6 text-[#0f2d5c]" />
        <div>
          <h1 className="text-[22px] font-black text-slate-900">Review Queue</h1>
          <p className="text-[13px] text-slate-400 mt-0.5">{pending.length} pending · manager / admin only</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">{Array.from({length:4}).map((_,i)=><Skeleton key={i} className="h-20 rounded-xl"/>)}</div>
      ) : (
        <>
          {/* Pending */}
          {pending.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-3 bg-amber-50 border-b border-amber-200">
                <h2 className="text-[13px] font-bold text-amber-800">Pending Review ({pending.length})</h2>
              </div>
              <div className="divide-y divide-slate-100">
                {pending.map(r => (
                  <div key={r.id} className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-[11px] font-bold text-slate-600 shrink-0">
                          {r.full_name.split(' ').map(n=>n[0]).join('').slice(0,2)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Link href={`/customers/${r.customer_id}`} className="text-[13px] font-semibold text-slate-800 hover:text-[#0f2d5c] transition-colors">
                              {r.full_name}
                            </Link>
                            <RiskBadge tier={r.risk_tier} />
                            <span className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded font-semibold">{r.action}</span>
                          </div>
                          <div className="flex items-center gap-3 mt-1">
                            <div className="w-24"><ScoreBar score={r.churn_score} tier={r.risk_tier} height={4} showLabel /></div>
                            <span className="text-[10px] text-slate-400">{new Date(r.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {actId === r.id ? (
                          <div className="flex items-center gap-2">
                            <input value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Notes (optional)"
                              className="text-[12px] px-2 py-1 rounded border border-slate-200 bg-slate-50 focus:outline-none w-40" />
                            <button onClick={() => handleAction(r.id, 'approve')}
                              className="px-3 py-1 text-[11px] font-bold bg-green-600 text-white rounded-lg hover:bg-green-700">
                              Approve
                            </button>
                            <button onClick={() => handleAction(r.id, 'reject')}
                              className="px-3 py-1 text-[11px] font-bold bg-red-600 text-white rounded-lg hover:bg-red-700">
                              Reject
                            </button>
                            <button onClick={() => setActId('')} className="text-slate-400 hover:text-slate-600 text-[16px]">×</button>
                          </div>
                        ) : (
                          <button onClick={() => setActId(r.id)}
                            className="px-3 py-1.5 text-[12px] font-semibold bg-[#0f2d5c] text-white rounded-lg hover:bg-[#1a3f7a] transition-colors">
                            Review
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completed */}
          {completed.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-200">
                <h2 className="text-[13px] font-bold text-slate-700">Completed ({completed.length})</h2>
              </div>
              <div className="divide-y divide-slate-100">
                {completed.map(r => (
                  <div key={r.id} className="flex items-center gap-3 px-4 py-3">
                    {r.status === 'approved'
                      ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                      : <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                    }
                    <div className="flex-1">
                      <span className="text-[12px] font-semibold text-slate-800">{r.full_name}</span>
                      <span className="text-[10px] text-slate-400 ml-2">{r.action}</span>
                      {r.notes && <p className="text-[11px] text-slate-500 mt-0.5">"{r.notes}"</p>}
                    </div>
                    <RiskBadge tier={r.risk_tier} />
                    <span className={`text-[10px] font-semibold capitalize ${r.status==='approved'?'text-green-600':'text-red-600'}`}>{r.status}</span>
                    <span className="text-[10px] text-slate-400">{r.reviewer}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {reviews.length === 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
              <Shield className="w-8 h-8 text-slate-200 mx-auto mb-3" />
              <p className="text-[14px] text-slate-400">No reviews in the queue.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
