"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useOutreachStream } from "@/hooks/useOutreachStream";
import { AnalysisResult } from "@/types";
import { Sparkles, Mail, MessageSquare, Smartphone, Copy, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

interface OutreachPanelProps {
    customerId: string;
    analysisResult: AnalysisResult;
}

export function OutreachPanel({ customerId, analysisResult }: OutreachPanelProps) {
    const [channel, setChannel] = useState<string>("email");
    const [copied, setCopied] = useState(false);

    const { content, isStreaming, isComplete, error, startStream, reset } = useOutreachStream();

    const handleGenerate = () => {
        startStream(customerId, channel, analysisResult);
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(content);
        setCopied(true);
        toast("Copied to clipboard");
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <Card className="shadow-sm border-purple-200 mt-6 overflow-hidden">
            <div className="h-1 w-full bg-gradient-to-r from-purple-400 to-indigo-500" />
            <CardHeader className="pb-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <CardTitle className="text-base font-semibold text-slate-900 flex items-center">
                        <Sparkles className="w-5 h-5 mr-2 text-purple-600" />
                        Outreach Intelligence · Personalised Engagement
                    </CardTitle>

                    <div className="flex bg-slate-100 p-1 rounded-lg">
                        <button
                            onClick={() => { setChannel("email"); reset(); }}
                            className={`flex items-center min-w-24 justify-center text-xs font-medium px-3 py-1.5 rounded-md transition-all ${channel === 'email' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            <Mail className="w-3.5 h-3.5 mr-1.5" /> Email
                        </button>
                        <button
                            onClick={() => { setChannel("sms"); reset(); }}
                            className={`flex items-center min-w-24 justify-center text-xs font-medium px-3 py-1.5 rounded-md transition-all ${channel === 'sms' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            <MessageSquare className="w-3.5 h-3.5 mr-1.5" /> SMS
                        </button>
                        <button
                            onClick={() => { setChannel("in_app"); reset(); }}
                            className={`flex items-center min-w-24 justify-center text-xs font-medium px-3 py-1.5 rounded-md transition-all ${channel === 'in_app' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            <Smartphone className="w-3.5 h-3.5 mr-1.5" /> In-App
                        </button>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="pt-2">
                {!content && !isStreaming && !error ? (
                    <div className="flex flex-col items-center justify-center py-10 border border-dashed border-purple-100 rounded-lg bg-gradient-to-b from-purple-50/40 to-indigo-50/30">
                        <div className="flex items-center gap-1.5 mb-3">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-purple-400 px-2 py-0.5 bg-purple-100 rounded-full">Powered by NVIDIA · DeepSeek V4 Pro</span>
                        </div>
                        <Button
                            onClick={handleGenerate}
                            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-md h-10 px-6 font-semibold tracking-wide"
                        >
                            <Sparkles className="w-4 h-4 mr-2" />
                            Generate Personalised Outreach
                        </Button>
                        <p className="text-xs text-slate-400 mt-3 text-center max-w-sm">
                            Action Intelligence + Outreach Engine — synthesises all risk signals and life events into a channel-optimised retention message.
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        <div className="relative w-full border border-slate-200 rounded-lg bg-white p-6 shadow-inner min-h-[160px]">
                            <div className="font-serif text-slate-800 whitespace-pre-wrap leading-relaxed">
                                {content}
                                {isStreaming && (
                                    <span className="inline-block w-1.5 h-4 ml-1 bg-slate-400 animate-pulse align-middle" />
                                )}
                            </div>

                            {isComplete && (
                                <div className="absolute top-4 right-4 flex gap-2">
                                    <Button variant="outline" size="icon" className="h-8 w-8 text-slate-500 bg-white" onClick={handleCopy}>
                                        {copied ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                                    </Button>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-between items-center">
                            <div>
                                {isStreaming && (
                                    <span className="text-xs font-semibold text-purple-600 flex items-center">
                                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse mr-2" />
                                        Generating...
                                    </span>
                                )}
                                {error && (
                                    <span className="text-xs font-semibold text-red-500">Error generating outreach.</span>
                                )}
                            </div>

                            {isComplete && (
                                <Button variant="ghost" size="sm" onClick={handleGenerate} className="text-purple-700 hover:bg-purple-50 font-semibold">
                                    <Sparkles className="w-4 h-4 mr-2" />
                                    Refresh Outreach
                                </Button>
                            )}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
