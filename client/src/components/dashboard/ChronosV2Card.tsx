"use client";

import { V2ModelHealth, PortfolioSurvival } from "@/types";
import { Activity, Network, Brain, GitBranch, Layers, AlertTriangle, CheckCircle2 } from "lucide-react";

interface ChronosV2CardProps {
    modelHealth: V2ModelHealth | null;
    portfolioSurvival: PortfolioSurvival | null;
    loading: boolean;
}

const URGENCY_CONFIG = {
    "7d":  { label: "7-Day Alert",  bg: "bg-red-500",    text: "text-red-700" },
    "30d": { label: "30-Day Risk",  bg: "bg-amber-500",  text: "text-amber-700" },
    "90d": { label: "90-Day Watch", bg: "bg-yellow-500", text: "text-yellow-700" },
    "safe":{ label: "Stable",       bg: "bg-emerald-500",text: "text-emerald-700" },
} as const;

const MODEL_ICONS: Record<string, React.ReactNode> = {
    tare:      <Brain className="w-3.5 h-3.5" />,
    graph:     <Network className="w-3.5 h-3.5" />,
    deephit:   <Activity className="w-3.5 h-3.5" />,
    fusionxv2: <Layers className="w-3.5 h-3.5" />,
};

function MetricPill({ label, value, sub }: { label: string; value: string; sub?: string }) {
    return (
        <div className="bg-indigo-50/70 rounded-lg p-3 border border-indigo-100/60 flex flex-col">
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider mb-1">{label}</span>
            <span className="text-lg font-bold text-slate-900 leading-none">{value}</span>
            {sub && <span className="text-[10px] text-slate-400 mt-0.5">{sub}</span>}
        </div>
    );
}

export function ChronosV2Card({ modelHealth, portfolioSurvival, loading }: ChronosV2CardProps) {
    if (loading) {
        return (
            <div className="rounded-xl border border-indigo-200 bg-white overflow-hidden animate-pulse">
                <div className="px-5 py-4 bg-indigo-50 border-b border-indigo-200">
                    <div className="h-4 bg-indigo-200 rounded w-64" />
                </div>
                <div className="p-5 space-y-4">
                    <div className="grid grid-cols-4 gap-3">
                        {[1,2,3,4].map(i => <div key={i} className="h-16 bg-slate-100 rounded-lg" />)}
                    </div>
                    <div className="h-12 bg-slate-100 rounded-lg" />
                </div>
            </div>
        );
    }

    if (!modelHealth && !portfolioSurvival) return null;

    const total = portfolioSurvival?.total ?? 0;
    const urgencyKeys = ["7d", "30d", "90d", "safe"] as const;

    return (
        <div className="rounded-xl border border-indigo-200/80 bg-white overflow-hidden">
            {/* Header */}
            <div className="px-5 py-3 bg-gradient-to-r from-indigo-50 to-violet-50 border-b border-indigo-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    <GitBranch className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-bold text-slate-800">Retention Intelligence · Precision Ensemble</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200 uppercase tracking-wider">
                        Network Intelligence + Survival Analytics + Temporal Patterns
                    </span>
                </div>
                {modelHealth?.ensemble?.last_calibrated && (
                    <span className="text-[10px] text-slate-400 font-mono">
                        calibrated {new Date(modelHealth.ensemble.last_calibrated).toLocaleDateString()}
                    </span>
                )}
            </div>

            <div className="p-5 space-y-5">
                {/* Model cards */}
                {modelHealth?.models && modelHealth.models.length > 0 && (
                    <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Model Components</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {modelHealth.models.map(m => (
                                <div key={m.name} className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-1.5 text-slate-600">
                                            {(() => {
                                                const n = m.name.toLowerCase();
                                                if (n.includes('graph')) return MODEL_ICONS.graph;
                                                if (n.includes('deephit')) return MODEL_ICONS.deephit;
                                                if (n.includes('fusion')) return MODEL_ICONS.fusionxv2;
                                                return MODEL_ICONS.tare;
                                            })()}
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider truncate max-w-[80px]">{m.name}</span>
                                        </div>
                                        {m.status === "active" ? (
                                            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                        ) : (
                                            <AlertTriangle className="w-3 h-3 text-amber-500" />
                                        )}
                                    </div>
                                    {m.auc && (
                                        <div className="mb-1">
                                            <span className="text-xs text-slate-400">AUC </span>
                                            <span className="text-sm font-bold text-indigo-700">{m.auc.toFixed(3)}</span>
                                        </div>
                                    )}
                                    {m.val_loss && (
                                        <div className="mb-1">
                                            <span className="text-xs text-slate-400">val_loss </span>
                                            <span className="text-sm font-bold text-violet-700">{m.val_loss.toFixed(3)}</span>
                                        </div>
                                    )}
                                    {m.weights && (
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {Object.entries(m.weights).map(([k, v]) => (
                                                <span key={k} className="text-[9px] font-mono bg-indigo-50 text-indigo-600 px-1 rounded">
                                                    {k} {Math.round(v * 100)}%
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    <p className="text-[9px] text-slate-400 mt-1.5 font-mono">{m.version}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Portfolio survival urgency distribution */}
                {portfolioSurvival && (
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Portfolio Urgency Distribution</p>
                            <span className="text-[10px] text-slate-400">{total} customers</span>
                        </div>
                        <div className="flex gap-1 h-7 rounded-full overflow-hidden">
                            {urgencyKeys.map(k => {
                                const count = portfolioSurvival.by_urgency?.[k] ?? 0;
                                const pct = total > 0 ? (count / total) * 100 : 0;
                                const cfg = URGENCY_CONFIG[k];
                                if (pct === 0) return null;
                                return (
                                    <div
                                        key={k}
                                        className={`${cfg.bg} flex items-center justify-center transition-all`}
                                        style={{ width: `${pct}%` }}
                                        title={`${cfg.label}: ${count} (${Math.round(pct)}%)`}
                                    >
                                        {pct > 10 && (
                                            <span className="text-white text-[9px] font-bold">{Math.round(pct)}%</span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                        <div className="flex gap-3 mt-2 flex-wrap">
                            {urgencyKeys.map(k => {
                                const count = portfolioSurvival.by_urgency?.[k] ?? 0;
                                const cfg = URGENCY_CONFIG[k];
                                return (
                                    <div key={k} className="flex items-center gap-1.5">
                                        <div className={`w-2 h-2 rounded-full ${cfg.bg}`} />
                                        <span className="text-[10px] text-slate-500">{cfg.label}: <strong className={cfg.text}>{count}</strong></span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Avg survival metrics */}
                {portfolioSurvival && (
                    <div className="grid grid-cols-3 gap-3">
                        <MetricPill
                            label="Avg P(churn 7d)"
                            value={`${Math.round((portfolioSurvival.avg_survival_7d ?? 0) * 100)}%`}
                            sub="portfolio-wide"
                        />
                        <MetricPill
                            label="Avg P(churn 30d)"
                            value={`${Math.round((portfolioSurvival.avg_survival_30d ?? 0) * 100)}%`}
                            sub="portfolio-wide"
                        />
                        <MetricPill
                            label="Avg Disagreement"
                            value={`±${Math.round((portfolioSurvival.avg_disagreement ?? 0) * 100)}%`}
                            sub="ensemble spread"
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
