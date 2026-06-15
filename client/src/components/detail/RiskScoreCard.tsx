"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskTier } from "@/types";
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from "recharts";
import { RiskBadge } from "@/components/customers/RiskBadge";

interface RiskScoreCardProps {
    score: number;
    tier: RiskTier;
    recommendedAction: string;
    reasonCodes: string[];
}

export function RiskScoreCard({ score, tier, recommendedAction, reasonCodes }: RiskScoreCardProps) {
    const getTierColor = (t: string) => {
        switch (t) {
            case 'critical': return '#EF4444';
            case 'high': return '#F97316';
            case 'medium': return '#EAB308';
            case 'watch': return '#3B82F6';
            case 'low': return '#22C55E';
            default: return '#94A3B8';
        }
    };

    const data = [{
        name: "Score",
        value: score * 100,
        fill: getTierColor(tier)
    }];

    return (
        <Card className="shadow-sm border-gray-200 h-full flex flex-col">
            <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-900">Risk Assessment</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col pt-0">
                <div className="flex justify-between items-center gap-4">
                    <div className="h-32 w-32 relative flex-shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadialBarChart
                                cx="50%" cy="50%" innerRadius="70%" outerRadius="100%"
                                barSize={12} data={data} startAngle={180} endAngle={0}
                            >
                                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                                <RadialBar
                                    background={{ fill: '#f1f5f9' }}
                                    dataKey="value"
                                    cornerRadius={10}
                                />
                            </RadialBarChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center pt-10">
                            <span className="text-2xl font-bold text-slate-900 leading-none">{Math.round(score * 100)}%</span>
                        </div>
                    </div>

                    <div className="flex-1 h-32 flex flex-col justify-center">
                        <RiskBadge tier={tier} className="w-fit mb-3 text-sm px-3 py-1" />
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Recommended Action</div>
                        <div className="text-sm font-semibold text-slate-900">{recommendedAction || 'Monitor Account'}</div>
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-100 flex-1">
                    <div className="text-sm font-medium text-slate-700 mb-2">Key Value Drivers</div>
                    {reasonCodes && reasonCodes.length > 0 ? (
                        <ul className="space-y-1.5 list-disc pl-4 text-sm text-slate-600">
                            {reasonCodes.map((reason, i) => (
                                <li key={i}>{reason}</li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-sm text-slate-500 italic">No formal reason codes available (run analysis to generate).</p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
