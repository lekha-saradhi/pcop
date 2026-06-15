"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface ChurnTrendChartProps {
    data: { week: string; avg_score: number; date?: string }[];
}

function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2">
            <p className="text-[11px] font-bold text-slate-500 mb-0.5">{payload[0]?.payload?.date || label}</p>
            <p className="text-sm font-bold text-blue-700">{(payload[0]?.value * 100).toFixed(1)}% avg churn risk</p>
        </div>
    );
}

export function ChurnTrendChart({ data = [] }: ChurnTrendChartProps) {
    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm h-full">
            <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-800">Portfolio Churn Score Trend</p>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100 uppercase tracking-wider">12 weeks</span>
            </div>
            <div className="h-[200px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="churnGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%"  stopColor="#2563EB" stopOpacity={0.15} />
                                <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                        <XAxis
                            dataKey="week"
                            axisLine={false} tickLine={false}
                            tick={{ fontSize: 11, fill: '#94A3B8' }} dy={8}
                        />
                        <YAxis
                            domain={[0.2, 0.9]}
                            axisLine={false} tickLine={false}
                            tick={{ fontSize: 11, fill: '#94A3B8' }}
                            tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="avg_score"
                            stroke="#2563EB"
                            strokeWidth={2}
                            fill="url(#churnGrad)"
                            dot={false}
                            activeDot={{ r: 4, fill: "#2563EB", stroke: "#fff", strokeWidth: 2 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
