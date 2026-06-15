"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { ReviewActionType, ReviewStatus } from "@/types";

const ACTIONS: { action: ReviewActionType; label: string; color: string; description: string }[] = [
    { action: "start_review", label: "Start Review", color: "bg-blue-600 hover:bg-blue-700 text-white", description: "Begin reviewing this case" },
    { action: "approve", label: "Approve", color: "bg-emerald-600 hover:bg-emerald-700 text-white", description: "Approve and close this case" },
    { action: "reject", label: "Reject", color: "bg-red-600 hover:bg-red-700 text-white", description: "Reject and close this case" },
    { action: "escalate", label: "Escalate", color: "bg-violet-600 hover:bg-violet-700 text-white", description: "Escalate to senior officer" },
    { action: "comment", label: "Add Note", color: "bg-slate-600 hover:bg-slate-700 text-white", description: "Add a comment without changing status" },
];

export function ReviewActionPanel({
    currentStatus,
    onAction,
    loading,
}: {
    currentStatus: ReviewStatus;
    onAction: (action: ReviewActionType, comment: string) => void;
    loading: boolean;
}) {
    const [comment, setComment] = useState("");
    const [selectedAction, setSelectedAction] = useState<ReviewActionType | null>(null);

    const allowedActions = ACTIONS.filter((a) => {
        if (currentStatus === "approved" || currentStatus === "rejected") return false;
        if (currentStatus === "pending" && a.action === "start_review") return true;
        if (currentStatus === "in_review" && a.action === "start_review") return false;
        return a.action !== "start_review";
    });

    const handleClick = (action: ReviewActionType) => {
        setSelectedAction(action);
        if (action === "comment" && !comment.trim()) return;
        onAction(action, comment);
    };

    return (
        <div className="space-y-3">
            <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Comment</label>
                <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Add your notes, reasoning, or instructions..."
                    rows={3}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
            </div>

            <div className="flex flex-wrap gap-2">
                {allowedActions.map((a) => (
                    <Button
                        key={a.action}
                        onClick={() => handleClick(a.action)}
                        disabled={loading || selectedAction === a.action}
                        size="sm"
                        className={`text-xs px-3 py-1.5 h-auto ${a.color}`}
                    >
                        {loading && selectedAction === a.action ? "Processing..." : a.label}
                    </Button>
                ))}
            </div>
        </div>
    );
}
