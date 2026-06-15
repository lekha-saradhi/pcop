"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { ExternalLink, MapPin, Building2, Clock, Activity } from "lucide-react";
import type { Customer, Signal } from "@/types";
import { tierColor } from "@/components/RiskBadge";

interface SnapshotData {
    customer: Customer;
    signals:  Signal[];
}

export function CustomerSnapshot({ customerId }: { customerId: string }) {
    const [data, setData] = useState<SnapshotData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!customerId) return;
        setLoading(true);
        api.getCustomerById(customerId)
            .then((res) => setData({ customer: res.customer, signals: res.signals ?? [] }))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [customerId]);

    if (loading) {
        return (
            <div className="space-y-3 p-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-16 w-full rounded-lg" />
            </div>
        );
    }

    if (!data) {
        return <p className="text-xs text-slate-400 py-4 text-center">Customer data unavailable</p>;
    }

    const c = data.customer;
    const color = tierColor(c.risk_tier);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <Link href={`/customers/${c.customer_id}`}
                        className="flex items-center gap-1.5 text-sm font-semibold text-[#0f2d5c] hover:underline">
                        {c.full_name}
                        <ExternalLink className="w-3 h-3" />
                    </Link>
                    <p className="text-[10px] text-slate-400 mt-0.5">{c.customer_id}</p>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                    style={{ color, borderColor: color, backgroundColor: `${color}14` }}>
                    {c.risk_tier}
                </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                    <MapPin className="w-3 h-3 text-slate-400" />
                    {c.city}
                </div>
                <div className="flex items-center gap-1.5">
                    <Building2 className="w-3 h-3 text-slate-400" />
                    {c.segment}
                </div>
                <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-slate-400" />
                    {c.tenure_months}mo tenure
                </div>
                <div className="flex items-center gap-1.5">
                    <Activity className="w-3 h-3 text-slate-400" />
                    {c.inactivity_days}d inactive
                </div>
            </div>

            <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase mb-1">Churn Score</p>
                <p className="text-2xl font-black tabular-nums" style={{ color }}>
                    {(c.churn_score * 100).toFixed(0)}%
                </p>
                <div className="w-full bg-slate-100 rounded-full h-1.5 mt-1">
                    <div className="h-1.5 rounded-full transition-all"
                        style={{ width: `${c.churn_score * 100}%`, backgroundColor: color }} />
                </div>
            </div>

            {c.life_event && (
                <div className="px-2 py-1.5 rounded-lg bg-purple-50 border border-purple-200">
                    <p className="text-[10px] font-semibold text-purple-700">
                        {c.life_event.replace(/_/g, ' ')}
                    </p>
                </div>
            )}

            {data.signals.length > 0 && (
                <div>
                    <p className="text-[10px] font-semibold text-slate-400 uppercase mb-1.5">
                        Active Signals ({data.signals.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                        {data.signals.slice(0, 4).map((s) => (
                            <Badge key={s.signal_type} variant="outline" className="text-[9px] font-medium capitalize">
                                {s.signal_type.replace(/_/g, ' ')}
                            </Badge>
                        ))}
                        {data.signals.length > 4 && (
                            <Badge variant="outline" className="text-[9px]">
                                +{data.signals.length - 4} more
                            </Badge>
                        )}
                    </div>
                </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-slate-100">
                <div>
                    <p className="text-[10px] font-semibold text-slate-400">Balance</p>
                    <p className="text-slate-700">₹{(c.balance / 1000).toFixed(0)}K</p>
                </div>
                <div>
                    <p className="text-[10px] font-semibold text-slate-400">Products</p>
                    <p className="text-slate-700">{c.product_count}</p>
                </div>
            </div>
        </div>
    );
}
