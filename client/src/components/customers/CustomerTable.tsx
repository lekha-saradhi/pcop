"use client";

import { useRouter } from "next/navigation";
import { Customer } from "@/types";
import { RiskBadge } from "@/components/customers/RiskBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";

interface CustomerTableProps {
    customers: Customer[];
    isLoading: boolean;
    v2ScoreMap?: Record<string, any>;
}

const URGENCY_STYLE: Record<string, { label: string; cls: string }> = {
    "7d":  { label: "7d Alert",  cls: "bg-red-100 text-red-700 border-red-200" },
    "30d": { label: "30d Risk",  cls: "bg-amber-100 text-amber-700 border-amber-200" },
    "90d": { label: "90d Watch", cls: "bg-yellow-100 text-yellow-700 border-yellow-200" },
};

function UrgencyBadge({ horizon }: { horizon: string | null | undefined }) {
    if (!horizon) return <span className="text-[10px] text-slate-400">—</span>;
    const cfg = URGENCY_STYLE[horizon];
    if (!cfg) return null;
    return (
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${cfg.cls} uppercase tracking-wider`}>
            {cfg.label}
        </span>
    );
}

export function CustomerTable({ customers, isLoading, Map = {} }: CustomerTableProps) {
    const router = useRouter();

    const formatSignals = (signals: string[]) => {
        if (!signals || signals.length === 0) return null;
        const items = signals.slice(0, 2).map(s =>
            s.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
        );
        const extra = signals.length > 2 ? `+${signals.length - 2} more` : '';

        return (
            <div className="flex flex-wrap gap-1">
                {items.map((item, idx) => (
                    <span key={idx} className="bg-slate-100 text-slate-600 text-[10px] px-1.5 py-0.5 rounded-sm whitespace-nowrap">
                        {item}
                    </span>
                ))}
                {extra && <span className="text-[10px] text-slate-500 ml-1 italic">{extra}</span>}
            </div>
        );
    };

    if (isLoading) {
        return (
            <div className="w-full h-64 flex items-center justify-center border border-slate-200 rounded-md bg-white">
                <p className="text-sm text-slate-500">Loading customers...</p>
            </div>
        );
    }

    if (customers.length === 0) {
        return (
            <div className="w-full h-64 flex flex-col items-center justify-center border border-slate-200 rounded-md bg-white">
                <p className="text-sm text-slate-500 font-medium pb-1">No customers found</p>
                <p className="text-xs text-slate-400">Try adjusting your filters.</p>
            </div>
        );
    }

    return (
        <div className="border border-slate-200 rounded-md bg-white overflow-hidden">
            <Table>
                <TableHeader className="bg-slate-50">
                    <TableRow>
                        <TableHead className="w-[120px] font-semibold text-slate-700">Customer ID</TableHead>
                        <TableHead className="font-semibold text-slate-700">Name</TableHead>
                        <TableHead className="font-semibold text-slate-700">Segment / Location</TableHead>
                        <TableHead className="font-semibold text-slate-700">Tenure</TableHead>
                        <TableHead className="w-[140px] font-semibold text-slate-700">Churn Score</TableHead>
                        <TableHead className="w-[100px] font-semibold text-slate-700">Risk Tier</TableHead>
                        <TableHead className="w-[200px] font-semibold text-slate-700">Active Signals</TableHead>
                        <TableHead className="w-[90px] font-semibold text-slate-700">Urgency</TableHead>
                        <TableHead className="text-right font-semibold text-slate-700">Action</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {customers.map((c) => (
                        <TableRow
                            key={c.customer_id}
                            className="cursor-pointer hover:bg-slate-50 transition-colors"
                            onClick={() => router.push(`/customers/${c.customer_id}`)}
                        >
                            <TableCell className="font-mono text-xs text-slate-500">{c.customer_id}</TableCell>
                            <TableCell className="font-medium text-sm text-slate-900">{c.full_name}</TableCell>
                            <TableCell>
                                <div className="text-sm text-slate-700">{c.segment}</div>
                                <div className="text-xs text-slate-400">{c.city}</div>
                            </TableCell>
                            <TableCell className="text-sm text-slate-600">{c.tenure_years} yrs</TableCell>
                            <TableCell>
                                <div className="w-full pr-4">
                                    <div className="flex justify-between items-end mb-1">
                                        <span className="text-sm font-semibold">{Math.round(c.churn_score * 100)}%</span>
                                    </div>
                                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                                        <div
                                            className="h-1.5 rounded-full"
                                            style={{
                                                width: `${c.churn_score * 100}%`,
                                                backgroundColor: c.risk_tier === 'critical' ? '#EF4444' :
                                                    c.risk_tier === 'high' ? '#F97316' :
                                                        c.risk_tier === 'medium' ? '#EAB308' :
                                                            c.risk_tier === 'watch' ? '#3B82F6' : '#22C55E'
                                            }}
                                        ></div>
                                    </div>
                                </div>
                            </TableCell>
                            <TableCell>
                                <RiskBadge tier={c.risk_tier} />
                            </TableCell>
                            <TableCell>
                                {formatSignals(c.active_signals)}
                            </TableCell>
                            <TableCell>
                                <UrgencyBadge horizon={v2ScoreMap[c.customer_id]?.urgency_horizon} />
                            </TableCell>
                            <TableCell className="text-right">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 md:px-2 lg:px-4 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        router.push(`/customers/${c.customer_id}`);
                                    }}
                                >
                                    View
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
