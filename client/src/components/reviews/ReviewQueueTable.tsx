"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ReviewCase, ReviewStatus, ReviewType, ReviewPriority } from "@/types";

const STATUS_STYLE: Record<ReviewStatus, string> = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    in_review: "bg-blue-50 text-blue-700 border-blue-200",
    approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
    rejected: "bg-red-50 text-red-700 border-red-200",
    escalated: "bg-violet-50 text-violet-700 border-violet-200",
};

const PRIORITY_STYLE: Record<ReviewPriority, string> = {
    critical: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800",
    medium: "bg-blue-100 text-blue-800",
    low: "bg-slate-100 text-slate-800",
};

const TYPE_LABEL: Record<ReviewType, string> = {
    score_alert: "Score Alert",
    compliance_flag: "Compliance",
    outreach_approval: "Outreach",
    manual: "Manual",
};

export function ReviewQueueTable({
    cases,
    loading,
    onStatusFilter,
    onTypeFilter,
    onPriorityFilter,
    activeStatus,
    activeType,
    activePriority,
}: {
    cases: ReviewCase[];
    loading: boolean;
    onStatusFilter: (s: string) => void;
    onTypeFilter: (t: string) => void;
    onPriorityFilter: (p: string) => void;
    activeStatus: string;
    activeType: string;
    activePriority: string;
}) {
    const filters = [
        { label: "All", key: "status", value: "", onClick: () => onStatusFilter("") },
        { label: "Pending", key: "status", value: "pending", onClick: () => onStatusFilter("pending") },
        { label: "In Review", key: "status", value: "in_review", onClick: () => onStatusFilter("in_review") },
        { label: "Approved", key: "status", value: "approved", onClick: () => onStatusFilter("approved") },
        { label: "Rejected", key: "status", value: "rejected", onClick: () => onStatusFilter("rejected") },
    ];

    const typeFilters = [
        { label: "All", value: "", onClick: () => onTypeFilter("") },
        { label: "Score Alert", value: "score_alert", onClick: () => onTypeFilter("score_alert") },
        { label: "Compliance", value: "compliance_flag", onClick: () => onTypeFilter("compliance_flag") },
        { label: "Outreach", value: "outreach_approval", onClick: () => onTypeFilter("outreach_approval") },
        { label: "Manual", value: "manual", onClick: () => onTypeFilter("manual") },
    ];

    const priorityFilters = [
        { label: "All", value: "", onClick: () => onPriorityFilter("") },
        { label: "Critical", value: "critical", onClick: () => onPriorityFilter("critical") },
        { label: "High", value: "high", onClick: () => onPriorityFilter("high") },
        { label: "Medium", value: "medium", onClick: () => onPriorityFilter("medium") },
    ];

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
                {filters.map((f) => (
                    <button
                        key={f.label}
                        onClick={f.onClick}
                        className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
                            activeStatus === f.value
                                ? "bg-blue-600 text-white border-blue-600"
                                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                        }`}
                    >
                        {f.label}
                    </button>
                ))}
            </div>

            <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                <div className="flex items-center gap-1.5">
                    <span>Type:</span>
                    <select
                        value={activeType}
                        onChange={(e) => onTypeFilter(e.target.value)}
                        className="border border-slate-200 rounded px-2 py-1 text-xs"
                    >
                        {typeFilters.map((f) => (
                            <option key={f.value} value={f.value}>{f.label}</option>
                        ))}
                    </select>
                </div>
                <div className="flex items-center gap-1.5">
                    <span>Priority:</span>
                    <select
                        value={activePriority}
                        onChange={(e) => onPriorityFilter(e.target.value)}
                        className="border border-slate-200 rounded px-2 py-1 text-xs"
                    >
                        {priorityFilters.map((f) => (
                            <option key={f.value} value={f.value}>{f.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12 text-sm text-slate-400">Loading reviews...</div>
            ) : cases.length === 0 ? (
                <div className="text-center py-12 text-sm text-slate-400">No review cases found</div>
            ) : (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Case</th>
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Type</th>
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Priority</th>
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Status</th>
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Created</th>
                                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Assigned</th>
                                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {cases.map((c) => (
                                <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-4 py-3">
                                        <div className="font-medium text-slate-800">{c.title}</div>
                                        <div className="text-xs text-slate-400 mt-0.5">{c.customer_id}</div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <Badge variant="outline" className="text-[10px] font-medium">
                                            {TYPE_LABEL[c.type as ReviewType] || c.type}
                                        </Badge>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${PRIORITY_STYLE[c.priority as ReviewPriority] || ""}`}>
                                            {c.priority}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${STATUS_STYLE[c.status as ReviewStatus] || ""}`}>
                                            {c.status.replace("_", " ")}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-xs text-slate-500">
                                        {new Date(c.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                                    </td>
                                    <td className="px-4 py-3 text-xs text-slate-500">
                                        {c.assignedTo || "—"}
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <Link href={`/reviews/${c.id}`}>
                                            <Button variant="ghost" size="sm" className="text-xs h-7">
                                                Review
                                            </Button>
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
