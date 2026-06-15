'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

const TOKEN_COLORS: Record<string, string> = {
  CARD_SWIPE: '#3b82f6',
  CARD_TAP: '#60a5fa',
  ONLINE_PURCHASE: '#10b981',
  ONLINE_TRANSFER: '#34d399',
  BILL_PAYMENT: '#f59e0b',
  SUPPORT_CONTACT: '#f97316',
  COMPLAINT_RAISED: '#ef4444',
  INACTIVITY_7D: '#94a3b8',
  INACTIVITY_14D: '#64748b',
  INACTIVITY_30D: '#475569',
  PAD: '#e2e8f0',
};

const TOKEN_LABELS_SHORT: Record<string, string> = {
  CARD_SWIPE: 'CARD',
  CARD_TAP: 'TAP',
  ONLINE_PURCHASE: 'PURCHASE',
  ONLINE_TRANSFER: 'XFER',
  BILL_PAYMENT: 'BILL',
  SUPPORT_CONTACT: 'SUPPORT',
  COMPLAINT_RAISED: 'COMPLAINT',
};

interface TokenSequence {
  customer_id: string;
  token_ids: number[];
  time_gaps: number[];
  token_labels: string[];
  non_pad_count: number;
}

export function TokenTimeline({ customerId }: { customerId: string }) {
  const [data, setData] = useState<TokenSequence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    setLoading(true);
    api.getChronosTokenSequence(customerId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Failed to load token sequence'))
      .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) {
    return (
      <div className="animate-pulse bg-slate-100 rounded-lg h-24" />
    );
  }

  if (error || !data) {
    return null;
  }

  const nonPad = data.token_labels.filter(l => l !== 'PAD');
  const counts: Record<string, number> = {};
  for (const label of nonPad) {
    counts[label] = (counts[label] || 0) + 1;
  }
  const sortedTokens = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
          TARE Token Sequence
        </h3>
        <span className="text-xs text-slate-500">
          {data.non_pad_count} events · 180 max
        </span>
      </div>

      <div className="flex h-4 rounded-full overflow-hidden gap-[1px]">
        {data.token_labels.slice(0, 180).map((label, i) => (
          <div
            key={i}
            className="flex-1 first:rounded-l-full last:rounded-r-full"
            style={{ backgroundColor: TOKEN_COLORS[label] || '#e2e8f0' }}
            title={`#${i}: ${label}`}
          />
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1.5">
        {sortedTokens.map(([label, count]) => (
          <div key={label} className="flex items-center gap-2 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: TOKEN_COLORS[label] || '#e2e8f0' }}
            />
            <span className="text-slate-600">{TOKEN_LABELS_SHORT[label] || label}</span>
            <span className="font-medium text-slate-800 ml-auto">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
