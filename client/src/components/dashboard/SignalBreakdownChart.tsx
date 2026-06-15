"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface SignalBreakdownChartProps {
    data: { signal_type: string; count: number }[];
}

const COLORS = ['#2563EB', '#7C3AED', '#DB2777', '#DC2626', '#EA580C', '#CA8A04', '#16A34A', '#0891B2'];

function CustomTooltip({ active, payload }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2">
            <p className="text-xs font-bold text-slate-700">{payload[0]?.payload?.signal_type}</p>
            <p className="text-sm font-bold text-blue-700">{payload[0]?.value} customers</p>
        </div>
    );
}

export function SignalBreakdownChart({ data = [] }: SignalBreakdownChartProps) {
    const sorted = [...data].sort((a, b) => b.count - a.count);

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm h-full">
            <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-800">Active Signal Distribution</p>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 uppercase tracking-wider">{sorted.length} signal types</span>
            </div>
            <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sorted} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
                        <XAxis type="number" hide />
                        <YAxis
                            type="category"
                            dataKey="signal_type"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fontSize: 11, fill: '#64748B' }}
                            width={130}
                            tickFormatter={(v: string) => v.split('_').map((w: string) => w[0].toUpperCase() + w.slice(1)).join(' ')}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F8FAFC' }} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18}>
                            {sorted.map((_, i) => (
                                <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
