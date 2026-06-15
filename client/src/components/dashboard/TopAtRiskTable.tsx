"use client";

import { useRouter } from "next/navigation";

interface TopAtRiskTableProps {
    data: any[];
}

const TIER_STYLE: Record<string, string> = {
    critical: "bg-red-100 text-red-700",
    high:     "bg-orange-100 text-orange-700",
    medium:   "bg-yellow-100 text-yellow-700",
    watch:    "bg-blue-100 text-blue-700",
    low:      "bg-emerald-100 text-emerald-700",
};

const TIER_BAR: Record<string, string> = {
    critical: "#EF4444",
    high:     "#F97316",
    medium:   "#EAB308",
    watch:    "#3B82F6",
    low:      "#22C55E",
};

export function TopAtRiskTable({ data = [] }: TopAtRiskTableProps) {
    const router = useRouter();

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">Top At-Risk Customers</p>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-100 uppercase tracking-wider">
                    {data.filter(d => d.risk_tier === 'critical').length} critical
                </span>
            </div>
            <div className="divide-y divide-slate-50">
                {data.length === 0 && (
                    <p className="text-center text-sm text-slate-400 py-10">No at-risk customers found.</p>
                )}
                {data.map((c) => (
                    <div
                        key={c.id}
                        onClick={() => router.push(`/customers/${c.id}`)}
                        className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors group"
                    >
                        {/* Avatar initial */}
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-600 shrink-0">
                            {c.full_name?.charAt(0) || "?"}
                        </div>

                        {/* Name + ID */}
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-900 truncate group-hover:text-blue-700 transition-colors">{c.full_name}</p>
                            <p className="text-[10px] font-mono text-slate-400">{c.id} · {c.segment}</p>
                        </div>

                        {/* Score bar */}
                        <div className="flex items-center gap-2 shrink-0">
                            <div className="w-20">
                                <div className="flex justify-between items-center mb-0.5">
                                    <span className="text-xs font-bold text-slate-700">{Math.round(c.churn_score * 100)}%</span>
                                </div>
                                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full"
                                        style={{ width: `${c.churn_score * 100}%`, backgroundColor: TIER_BAR[c.risk_tier] || '#94a3b8' }}
                                    />
                                </div>
                            </div>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${TIER_STYLE[c.risk_tier] || 'bg-slate-100 text-slate-600'}`}>
                                {c.risk_tier}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
            {data.length > 0 && (
                <div className="px-5 py-3 border-t border-slate-100 text-center">
                    <button
                        onClick={() => router.push('/customers')}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                    >
                        View all customers →
                    </button>
                </div>
            )}
        </div>
    );
}
