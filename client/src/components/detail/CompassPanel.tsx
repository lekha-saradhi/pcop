"use client";

import { ActionPlan } from "@/types";
import {
    Mail, MessageSquare, Smartphone, Phone, Users,
    Clock, Tag, Zap, ChevronRight, Gift
} from "lucide-react";

interface CompassPanelProps {
    plan: ActionPlan | null;
    loading?: boolean;
}

const CHANNEL_ICON: Record<string, React.ReactNode> = {
    email:    <Mail className="w-4 h-4" />,
    sms:      <MessageSquare className="w-4 h-4" />,
    app:      <Smartphone className="w-4 h-4" />,
    call:     <Phone className="w-4 h-4" />,
    rm_visit: <Users className="w-4 h-4" />,
};
const CHANNEL_LABEL: Record<string, string> = {
    email: "Email", sms: "SMS", app: "Push Notification",
    call: "Phone Call", rm_visit: "RM Visit",
};
const TIMING_LABEL: Record<string, string> = {
    within_24h: "Within 24 hours", within_48h: "Within 48 hours",
    within_7d: "Within 7 days", standard: "Standard",
};
const PRIORITY_CONFIG: Record<number, { label: string; bg: string; text: string; border: string }> = {
    1: { label: "PRIORITY 1", bg: "bg-red-50",    text: "text-red-700",    border: "border-red-200"    },
    2: { label: "PRIORITY 2", bg: "bg-amber-50",  text: "text-amber-700",  border: "border-amber-200"  },
    3: { label: "PRIORITY 3", bg: "bg-slate-50",  text: "text-slate-600",  border: "border-slate-200"  },
};

export function CompassPanel({ plan, loading }: CompassPanelProps) {
    if (loading) {
        return (
            <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-48" />
                <div className="space-y-3">
                    <div className="h-12 bg-slate-100 rounded-lg" />
                    <div className="h-20 bg-slate-100 rounded-lg" />
                </div>
            </div>
        );
    }

    if (!plan) {
        return (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 flex items-center gap-3 text-slate-500">
                <Zap className="w-4 h-4 shrink-0" />
                <span className="text-sm">Action Intelligence plan not yet available for this customer.</span>
            </div>
        );
    }

    const pCfg = PRIORITY_CONFIG[plan.priority] || PRIORITY_CONFIG[3];

    return (
        <div className="rounded-xl border border-violet-200 bg-white overflow-hidden">
            {/* Header */}
            <div className="px-5 py-3 bg-violet-50 border-b border-violet-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    <Zap className="w-4 h-4 text-violet-600" />
                    <span className="text-sm font-bold text-slate-800">Action Intelligence · Next Best Offer</span>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${pCfg.bg} ${pCfg.text} border ${pCfg.border} uppercase tracking-wider`}>
                    {pCfg.label}
                </span>
            </div>

            <div className="p-5 space-y-4">
                {/* Channel + timing */}
                <div className="flex gap-3">
                    <div className="flex-1 bg-violet-50 rounded-lg p-3 border border-violet-100 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-violet-100 flex items-center justify-center text-violet-600 shrink-0">
                            {CHANNEL_ICON[plan.channel] || <Mail className="w-4 h-4" />}
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Channel</p>
                            <p className="text-sm font-semibold text-slate-800">{CHANNEL_LABEL[plan.channel] || plan.channel}</p>
                        </div>
                    </div>
                    <div className="flex-1 bg-slate-50 rounded-lg p-3 border border-slate-100 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 shrink-0">
                            <Clock className="w-4 h-4" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Timing</p>
                            <p className="text-sm font-semibold text-slate-800">{TIMING_LABEL[plan.timing] || plan.timing}</p>
                        </div>
                    </div>
                </div>

                {/* Offer */}
                <div className="bg-emerald-50 rounded-lg p-3.5 border border-emerald-200 flex items-start gap-3">
                    <Gift className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                    <div>
                        <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider">Offer</span>
                            <code className="text-[10px] font-mono bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">{plan.offer_code}</code>
                        </div>
                        <p className="text-sm font-semibold text-slate-800">{plan.offer_description}</p>
                        <p className="text-sm text-emerald-700 font-bold mt-0.5">{plan.offer_value}</p>
                    </div>
                </div>

                {/* Tone & strategy badges */}
                <div className="flex flex-wrap gap-1.5">
                    {plan.tone_modifiers.map(t => (
                        <span key={t} className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 uppercase tracking-wider">
                            {t}
                        </span>
                    ))}
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 uppercase tracking-wider">
                        {plan.content_strategy.replace(/_/g, " ")}
                    </span>
                </div>

                {/* Rationale */}
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Recommendation Rationale</p>
                    <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 rounded-lg p-3 border border-slate-100">
                        {plan.rationale}
                    </p>
                </div>
            </div>
        </div>
    );
}
