"use client";

import type { ReviewActionEntry, ReviewActionType } from "@/types";

const ACTION_STYLE: Record<ReviewActionType, { color: string; bg: string }> = {
    approve: { color: "text-emerald-600", bg: "bg-emerald-100" },
    reject: { color: "text-red-600", bg: "bg-red-100" },
    escalate: { color: "text-violet-600", bg: "bg-violet-100" },
    comment: { color: "text-slate-600", bg: "bg-slate-100" },
    assign: { color: "text-blue-600", bg: "bg-blue-100" },
    start_review: { color: "text-blue-600", bg: "bg-blue-100" },
};

const ACTION_LABEL: Record<ReviewActionType, string> = {
    approve: "Approved",
    reject: "Rejected",
    escalate: "Escalated",
    comment: "Added note",
    assign: "Assigned",
    start_review: "Started review",
};

export function ReviewTimeline({ actions }: { actions: ReviewActionEntry[] }) {
    if (!actions || actions.length === 0) {
        return <p className="text-xs text-slate-400 py-4 text-center">No activity recorded yet</p>;
    }

    return (
        <div className="relative">
            {actions.map((a, i) => {
                const style = ACTION_STYLE[a.action] || { color: "text-slate-600", bg: "bg-slate-100" };
                const label = ACTION_LABEL[a.action] || a.action;
                const isLast = i === actions.length - 1;

                return (
                    <div key={a.id} className="flex gap-3 pb-4 relative">
                        {!isLast && (
                            <div className="absolute left-[11px] top-5 bottom-0 w-px bg-slate-200" />
                        )}
                        <div className={`w-6 h-6 rounded-full ${style.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                            <div className={`w-2 h-2 rounded-full ${style.color.replace("text-", "bg-")}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className={`text-xs font-semibold ${style.color}`}>{label}</span>
                                <span className="text-[10px] text-slate-400">
                                    {new Date(a.timestamp).toLocaleDateString("en-IN", {
                                        day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                                    })}
                                </span>
                            </div>
                            <p className="text-xs text-slate-600 mt-0.5">
                                {a.officerName}
                                {a.comment ? <span className="text-slate-400"> &mdash; &ldquo;{a.comment}&rdquo;</span> : ""}
                            </p>
                            {a.previousStatus !== a.newStatus && (
                                <p className="text-[10px] text-slate-400 mt-0.5">
                                    Status: {a.previousStatus.replace("_", " ")} → {a.newStatus.replace("_", " ")}
                                </p>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
