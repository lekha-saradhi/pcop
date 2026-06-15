"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Signal } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CopyX } from "lucide-react";

export function SignalPanel({ signals }: { signals: Signal[] }) {
    if (!signals || signals.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 bg-white rounded-lg border border-dashed border-slate-300">
                <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                    <CopyX className="w-6 h-6 text-slate-400" />
                </div>
                <h3 className="text-base font-medium text-slate-900 mb-1">No active signals</h3>
                <p className="text-sm text-slate-500 text-center max-w-sm">
                    No predictive churn signals currently detected for this customer.
                </p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {signals.map((sig, i) => (
                <Card key={i} className="shadow-sm border-gray-200 overflow-hidden flex flex-col">
                    <div className="h-1 bg-blue-500 w-full" />
                    <CardHeader className="pb-3">
                        <div className="flex justify-between items-start gap-2">
                            <CardTitle className="text-base font-semibold leading-tight text-slate-900">
                                {sig.signal_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                            </CardTitle>
                            <Badge variant="outline" className="font-mono text-[10px] uppercase text-slate-500 bg-slate-50 shrink-0">
                                {sig.method_used}
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col pt-0">
                        <div className="mb-4">
                            <div className="flex justify-between items-end mb-1.5">
                                <span className="text-xs font-medium text-slate-500">Confidence</span>
                                <span className="text-xs font-bold text-slate-700">{Math.round(sig.confidence * 100)}%</span>
                            </div>
                            <Progress value={sig.confidence * 100} className="h-1.5 bg-slate-100" />
                        </div>

                        <div className="flex-1">
                            <span className="text-xs font-medium text-slate-500 block mb-2">Evidence</span>
                            <ul className="space-y-2">
                                {sig.evidence.map((ev, idx) => (
                                    <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                                        <span className="mt-1.5 w-1 h-1 rounded-full bg-slate-400 shrink-0" />
                                        <span className="leading-snug">{ev}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
