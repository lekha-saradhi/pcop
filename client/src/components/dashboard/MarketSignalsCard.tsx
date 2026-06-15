"use client";

import { Globe, TrendingDown, Info, AlertTriangle } from "lucide-react";

interface MarketSignal {
    signal_id?: string;
    signal_type?: string;
    description?: string;
    severity?: string;
    detected_at?: string;
    // legacy shape
    city?: string;
    segment?: string;
    news_risk_flag?: boolean;
    news_summary?: string;
}

const SEV_CONFIG: Record<string, { icon: React.ReactNode; bg: string; text: string; border: string }> = {
    high:   { icon: <AlertTriangle className="w-3.5 h-3.5" />, bg: "bg-red-50",    text: "text-red-600",    border: "border-red-100" },
    medium: { icon: <TrendingDown className="w-3.5 h-3.5" />, bg: "bg-amber-50",  text: "text-amber-600",  border: "border-amber-100" },
    info:   { icon: <Info className="w-3.5 h-3.5" />,         bg: "bg-blue-50",   text: "text-blue-600",   border: "border-blue-100" },
};

export function MarketSignalsCard({ signals }: { signals: MarketSignal[] }) {
    if (!signals || signals.length === 0) {
        return (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                    <Globe className="w-4 h-4 text-slate-400" />
                    <p className="text-sm font-semibold text-slate-800">Market & Macro Signals</p>
                </div>
                <p className="text-sm text-slate-400 italic text-center py-6">No active market risk signals.</p>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
                <Globe className="w-4 h-4 text-blue-500" />
                <p className="text-sm font-semibold text-slate-800">Market & Macro Signals</p>
                <span className="ml-auto text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 uppercase tracking-wider">{signals.length} active</span>
            </div>
            <div className="flex flex-col gap-2">
                {signals.map((sig, idx) => {
                    // handle both data shapes
                    const desc = sig.description || sig.news_summary || "";
                    const sev  = sig.severity || (sig.news_risk_flag ? "high" : "info");
                    const label = sig.signal_type
                        ? sig.signal_type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())
                        : sig.city || "Signal";
                    const cfg = SEV_CONFIG[sev] || SEV_CONFIG.info;
                    const time = sig.detected_at
                        ? new Date(sig.detected_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
                        : "";

                    return (
                        <div key={idx} className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.bg} ${cfg.border}`}>
                            <div className={`mt-0.5 shrink-0 ${cfg.text}`}>{cfg.icon}</div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${cfg.text}`}>{label}</span>
                                    {time && <span className="text-[10px] text-slate-400 shrink-0">{time}</span>}
                                </div>
                                <p className="text-xs text-slate-600 mt-0.5 leading-snug line-clamp-2">{desc}</p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
