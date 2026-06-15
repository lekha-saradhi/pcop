"use client";

import { use, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Shield, AlertTriangle, FileText, UserCheck } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ReviewActionPanel } from "@/components/reviews/ReviewActionPanel";
import { ReviewTimeline } from "@/components/reviews/ReviewTimeline";
import { CustomerSnapshot } from "@/components/reviews/CustomerSnapshot";
import { useReviewDetail } from "@/hooks/useReviews";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { ReviewActionType, ReviewType, ReviewPriority, ReviewStatus } from "@/types";

const TYPE_ICON: Record<string, React.ElementType> = {
    score_alert: AlertTriangle,
    compliance_flag: Shield,
    outreach_approval: FileText,
    manual: UserCheck,
};

const TYPE_LABEL: Record<string, string> = {
    score_alert: "Score Alert",
    compliance_flag: "Compliance Flag",
    outreach_approval: "Outreach Approval",
    manual: "Manual Review",
};

const STATUS_STYLE: Record<string, string> = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    in_review: "bg-blue-50 text-blue-700 border-blue-200",
    approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
    rejected: "bg-red-50 text-red-700 border-red-200",
    escalated: "bg-violet-50 text-violet-700 border-violet-200",
};

export default function ReviewDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const router = useRouter();
    const { review, loading, error, refetch } = useReviewDetail(id);

    const handleAction = useCallback(async (action: ReviewActionType, comment: string) => {
        try {
            await api.takeReviewAction(id, { action, comment });
            toast.success(`Action '${action}' recorded`);
            refetch();
        } catch (e: unknown) {
            toast.error(e instanceof Error ? e.message : "Failed to record action");
        }
    }, [id, refetch]);

    if (loading) {
        return (
            <div className="p-6 max-w-7xl mx-auto">
                <div className="animate-pulse space-y-4">
                    <div className="h-6 w-48 bg-slate-200 rounded" />
                    <div className="h-32 bg-slate-200 rounded-lg" />
                    <div className="h-64 bg-slate-200 rounded-lg" />
                </div>
            </div>
        );
    }

    if (error || !review) {
        return (
            <div className="p-6 max-w-7xl mx-auto">
                <Link href="/reviews" className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline mb-4">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Back to reviews
                </Link>
                <p className="text-sm text-slate-500 mt-8">{error || "Review case not found"}</p>
            </div>
        );
    }

    const Icon = TYPE_ICON[review.type] || Shield;

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <Link href="/reviews" className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline">
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to reviews
            </Link>

            <div className="bg-white border border-slate-200 rounded-lg p-5">
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <h1 className="text-lg font-bold text-slate-900">{review.title}</h1>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${STATUS_STYLE[review.status] || ""}`}>
                                {review.status.replace("_", " ")}
                            </span>
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                            <Badge variant="outline" className="text-[10px] font-medium">
                                {TYPE_LABEL[review.type] || review.type}
                            </Badge>
                            <span>Priority: <strong className="text-slate-700">{review.priority}</strong></span>
                            <span>Case: <strong className="text-slate-700">{review.id}</strong></span>
                            <span>Customer: <strong className="text-slate-700">{review.customer_id}</strong></span>
                        </div>
                    </div>
                </div>
                <p className="text-sm text-slate-600 mt-4 leading-relaxed">{review.description}</p>
                <p className="text-[10px] text-slate-400 mt-2">Created {new Date(review.createdAt).toLocaleString("en-IN")} by {review.createdBy}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                <div className="lg:col-span-3 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-lg p-5">
                        <h2 className="text-sm font-bold text-slate-800 mb-4">Actions</h2>
                        <ReviewActionPanel currentStatus={review.status as ReviewStatus} onAction={handleAction} loading={false} />
                    </div>

                    <div className="bg-white border border-slate-200 rounded-lg p-5">
                        <h2 className="text-sm font-bold text-slate-800 mb-4">Activity Timeline</h2>
                        <ReviewTimeline actions={review.actions || []} />
                    </div>
                </div>

                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-slate-200 rounded-lg p-5">
                        <h2 className="text-sm font-bold text-slate-800 mb-4">Customer Snapshot</h2>
                        <CustomerSnapshot customerId={review.customer_id} />
                    </div>

                    {review.context && Object.keys(review.context).length > 0 && (
                        <div className="bg-white border border-slate-200 rounded-lg p-5">
                            <h2 className="text-sm font-bold text-slate-800 mb-3">Case Context</h2>
                            <div className="space-y-2 text-xs">
                                {Object.entries(review.context).map(([key, value]) => (
                                    <div key={key} className="flex items-start gap-2">
                                        <span className="font-medium text-slate-500 capitalize min-w-[100px]">{key.replace(/_/g, " ")}:</span>
                                        <span className="text-slate-700">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
