"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const COLORS: Record<string, string> = {
    critical: "#EF4444",
    high:     "#F97316",
    medium:   "#EAB308",
    watch:    "#3B82F6",
    low:      "#22C55E",
};

const TIER_LABEL: Record<string, string> = {
    critical: "Critical", high: "High", medium: "Medium", watch: "Watch", low: "Low",
};

interface RiskDistributionChartProps {
    data: { tier: string; count: number; percentage: number }[];
}

export function RiskDistributionChart({ data = [] }: RiskDistributionChartProps) {
    const total = data.reduce((s, d) => s + d.count, 0);

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm h-full">
            <p className="text-sm font-semibold text-slate-800 mb-4">Risk Distribution</p>
            <div className="flex items-center gap-6">
                <div className="relative w-36 h-36 shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%" cy="50%"
                                innerRadius={44} outerRadius={68}
                                paddingAngle={2}
                                dataKey="count" nameKey="tier"
                                startAngle={90} endAngle={-270}
                            >
                                {data.map((entry, i) => (
                                    <Cell key={i} fill={COLORS[entry.tier] || "#94a3b8"} strokeWidth={0} />
                                ))}
                            </Pie>
                            <Tooltip
                                formatter={(v, n) => [`${v} customers`, TIER_LABEL[String(n)] || n]}
                                contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: 12, padding: '6px 10px' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-2xl font-bold text-slate-900">{total}</span>
                        <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">total</span>
                    </div>
                </div>

                <div className="flex flex-col gap-2 flex-1">
                    {data.filter(d => d.count > 0).map(d => (
                        <div key={d.tier} className="flex items-center gap-2.5">
                            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[d.tier] || '#94a3b8' }} />
                            <span className="text-xs text-slate-600 flex-1 capitalize">{TIER_LABEL[d.tier] || d.tier}</span>
                            <span className="text-xs font-bold text-slate-800 tabular-nums w-5 text-right">{d.count}</span>
                            <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${d.percentage}%`, backgroundColor: COLORS[d.tier] || '#94a3b8' }} />
                            </div>
                            <span className="text-[10px] text-slate-400 tabular-nums w-8 text-right">{d.percentage}%</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
