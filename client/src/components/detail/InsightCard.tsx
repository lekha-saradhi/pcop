"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
    Activity, 
    MessageSquare, 
    AlertCircle, 
    Plane, 
    Clock, 
    Zap, 
    BarChart3,
    History
} from "lucide-react";

interface InsightCardProps {
    insights: {
        engagement: {
            days_since_last_login: number | null;
            total_sessions_30d: number;
            avg_session_duration_s: number;
            most_used_feature: string | null;
        };
        crm: {
            total_complaints: number;
            unresolved_count: number;
            avg_resolution_days: number;
            last_complaint_at: string | null;
        };
        stress: {
            stress_related_mcc_count: number;
            overdraft_related_txns: number;
        };
        location: {
            city: string;
            transaction_count: number;
            last_seen: string | null;
        }[];
    } | null;
}

export function InsightCard({ insights }: InsightCardProps) {
    if (!insights) return null;

    const { engagement, crm } = insights;
    const stress   = insights.stress   ?? { stress_related_mcc_count: 0, overdraft_related_txns: 0 };
    const location = insights.location ?? [];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Behavioral Engagement */}
            <Card className="shadow-sm border-slate-200">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <Activity className="w-4 h-4 mr-2 text-blue-500" />
                        App Engagement (30d)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-50 rounded-lg">
                            <div className="text-xs text-slate-500 mb-1 flex items-center">
                                <Zap className="w-3 h-3 mr-1" /> Total Sessions
                            </div>
                            <div className="text-lg font-bold text-slate-900">{engagement.total_sessions_30d}</div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg">
                            <div className="text-xs text-slate-500 mb-1 flex items-center">
                                <Clock className="w-3 h-3 mr-1" /> Avg Duration
                            </div>
                            <div className="text-lg font-bold text-slate-900">
                                {Math.round(engagement.avg_session_duration_s / 60)}m
                            </div>
                        </div>
                    </div>
                    {engagement.most_used_feature && (
                        <div className="mt-3 flex items-center justify-between px-1">
                            <span className="text-xs text-slate-500">Most Used Feature:</span>
                            <Badge variant="outline" className="text-[10px] uppercase font-bold text-blue-600 bg-blue-50 border-blue-100">
                                {engagement.most_used_feature.replace(/_/g, ' ')}
                            </Badge>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Relationship Health */}
            <Card className="shadow-sm border-slate-200">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <MessageSquare className="w-4 h-4 mr-2 text-purple-500" />
                        Relationship Health
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-50 rounded-lg">
                            <div className="text-xs text-slate-500 mb-1 flex items-center">
                                <BarChart3 className="w-3 h-3 mr-1" /> Resolution Speed
                            </div>
                            <div className={`text-lg font-bold ${crm.avg_resolution_days > 5 ? 'text-red-600' : 'text-slate-900'}`}>
                                {crm.avg_resolution_days > 0 ? `${Math.round(crm.avg_resolution_days)} days` : 'N/A'}
                            </div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg">
                            <div className="text-xs text-slate-500 mb-1 flex items-center">
                                <AlertCircle className="w-3 h-3 mr-1" /> Active Complaints
                            </div>
                            <div className={`text-lg font-bold ${crm.unresolved_count > 0 ? 'text-orange-600' : 'text-slate-900'}`}>
                                {crm.unresolved_count}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Financial Stress Indicators */}
            <Card className="shadow-sm border-slate-200">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <AlertCircle className="w-4 h-4 mr-2 text-red-500" />
                        Financial Stress Markers
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-between p-4 bg-red-50/50 rounded-lg border border-red-100">
                        <div>
                            <div className="text-xs text-red-700 font-semibold mb-1">Stress-Related MCC usage</div>
                            <div className="text-2xl font-black text-red-800">{stress.stress_related_mcc_count}</div>
                        </div>
                        <div className="text-right">
                            <div className="text-xs text-slate-500 mb-1 italic">Detects payday loans, etc.</div>
                            <Badge variant="outline" className={`text-[10px] ${stress.stress_related_mcc_count > 0 ? 'bg-red-100 text-red-700 border-red-200' : 'bg-green-100 text-green-700 border-green-200'}`}>
                                {stress.stress_related_mcc_count > 0 ? 'Elevated Alert' : 'Normal / Low'}
                            </Badge>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Location & Travel History */}
            <Card className="shadow-sm border-slate-200">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                        <Plane className="w-4 h-4 mr-2 text-indigo-500" />
                        Geographic Signal (180d)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {location.slice(0, 2).map((loc, idx) => (
                            <div key={idx} className="flex items-center justify-between text-sm py-1 border-b border-slate-50 last:border-0">
                                <div className="flex items-center">
                                    <History className="w-3.5 h-3.5 mr-2 text-slate-400" />
                                    <span className="font-medium text-slate-700">{loc.city}</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-xs text-slate-400">{loc.transaction_count} txns</span>
                                    <span className="text-[10px] text-slate-400 font-mono italic">
                                        Last: {loc.last_seen ? new Date(loc.last_seen).toLocaleDateString() : 'N/A'}
                                    </span>
                                </div>
                            </div>
                        ))}
                        {location.length === 0 && (
                            <div className="text-center py-4 text-xs text-slate-400 italic">No geographic variance detected.</div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
