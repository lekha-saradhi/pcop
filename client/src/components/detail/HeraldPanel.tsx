"use client";

import { HeraldContent } from "@/types";
import { useState } from "react";
import { Sparkles, Mail, MessageSquare, Smartphone, Phone, Users, ShieldCheck, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";

interface HeraldPanelProps {
    content: HeraldContent | null;
    loading?: boolean;
}

const CHANNEL_ICON: Record<string, React.ReactNode> = {
    email:    <Mail className="w-3.5 h-3.5" />,
    sms:      <MessageSquare className="w-3.5 h-3.5" />,
    app:      <Smartphone className="w-3.5 h-3.5" />,
    call:     <Phone className="w-3.5 h-3.5" />,
    rm_visit: <Users className="w-3.5 h-3.5" />,
};

function CopyBtn({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(text).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
    };
    return (
        <button onClick={copy} className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
    );
}

function EmailPreview({ content }: { content: HeraldContent }) {
    const [showAB, setShowAB] = useState(false);
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="space-y-3">
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-14 shrink-0">Subject</span>
                    <div className="flex-1 flex items-center justify-between bg-slate-50 rounded px-2.5 py-1.5 border border-slate-100">
                        <span className="text-sm font-semibold text-slate-800">{content.subject_line}</span>
                        <CopyBtn text={content.subject_line || ""} />
                    </div>
                </div>
                <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-14 shrink-0 pt-1.5">Preview</span>
                    <div className="flex-1 bg-slate-50 rounded px-2.5 py-1.5 border border-slate-100">
                        <span className="text-xs text-slate-500 italic">{content.preview_text}</span>
                    </div>
                </div>
            </div>

            <div>
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
                >
                    {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    {expanded ? "Hide" : "Show"} email body
                </button>
                {expanded && content.body && (
                    <div className="mt-2 relative">
                        <div className="bg-white border border-slate-200 rounded-lg p-4 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto">
                            {content.body}
                        </div>
                        <div className="absolute top-2 right-2">
                            <CopyBtn text={content.body} />
                        </div>
                    </div>
                )}
            </div>

            {content.ab_variant && (
                <div>
                    <button
                        onClick={() => setShowAB(!showAB)}
                        className="flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-700 transition-colors"
                    >
                        {showAB ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        A/B variant
                    </button>
                    {showAB && (
                        <div className="mt-2 space-y-1.5 bg-violet-50 rounded-lg p-3 border border-violet-100">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">Alt Subject</span>
                                <CopyBtn text={content.ab_variant.subject_line} />
                            </div>
                            <p className="text-sm text-violet-800 font-medium">{content.ab_variant.subject_line}</p>
                            <p className="text-xs text-violet-500 italic">{content.ab_variant.preview_text}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function SmsPreview({ content }: { content: HeraldContent }) {
    const body = content.body || "";
    return (
        <div className="space-y-2">
            <div className="flex items-start gap-2 justify-end">
                <div className="max-w-[85%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed shadow-sm">
                    {body}
                </div>
            </div>
            <div className="flex justify-between items-center text-[10px] text-slate-400">
                <span>{body.length}/160 chars</span>
                <CopyBtn text={body} />
            </div>
        </div>
    );
}

function PushPreview({ content }: { content: HeraldContent }) {
    return (
        <div className="bg-slate-900 rounded-xl p-4 text-white space-y-1">
            <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 bg-indigo-500 rounded-sm" />
                <span className="text-[10px] text-slate-400 font-medium">PCOP</span>
            </div>
            <p className="text-sm font-bold">{content.title}</p>
            <p className="text-xs text-slate-300 leading-snug">{content.body}</p>
            {content.cta && (
                <button className="mt-2 text-[11px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors">
                    {content.cta} →
                </button>
            )}
        </div>
    );
}

function CallBriefing({ content }: { content: HeraldContent }) {
    return (
        <div className="space-y-3">
            {content.opening && (
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Opening Line</p>
                    <p className="text-sm text-slate-700 italic">&ldquo;{content.opening}&rdquo;</p>
                </div>
            )}
            {content.talking_points && content.talking_points.length > 0 && (
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Talking Points</p>
                    <ol className="space-y-2">
                        {content.talking_points.map((tp, i) => (
                            <li key={i} className="flex gap-2.5">
                                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-violet-100 text-violet-700 text-[10px] font-bold flex items-center justify-center">{i+1}</span>
                                <span className="text-sm text-slate-700 leading-snug">{tp}</span>
                            </li>
                        ))}
                    </ol>
                </div>
            )}
        </div>
    );
}

export function HeraldPanel({ content, loading }: HeraldPanelProps) {
    if (loading) {
        return (
            <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-48" />
                <div className="h-16 bg-slate-100 rounded-lg" />
                <div className="h-8 bg-slate-100 rounded-lg" />
            </div>
        );
    }

    if (!content) {
        return (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 flex items-center gap-3 text-slate-500">
                <Sparkles className="w-4 h-4 shrink-0" />
                <span className="text-sm">HERALD content not yet generated for this customer.</span>
            </div>
        );
    }

    const channelIcon = CHANNEL_ICON[content.channel] || <Mail className="w-3.5 h-3.5" />;
    const channelLabel = { email: "Email", sms: "SMS", app: "Push", call: "Call Brief", rm_visit: "RM Brief" }[content.channel] || content.channel;

    return (
        <div className="rounded-xl border border-rose-200 bg-white overflow-hidden">
            {/* Header */}
            <div className="px-5 py-3 bg-rose-50 border-b border-rose-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    <Sparkles className="w-4 h-4 text-rose-500" />
                    <span className="text-sm font-bold text-slate-800">HERALD · Generated Content</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-white text-slate-600 border border-slate-200 uppercase tracking-wider">
                        {channelIcon} {channelLabel}
                    </span>
                    {content.compliance_status === "approved" && (
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <ShieldCheck className="w-2.5 h-2.5" /> Approved
                        </span>
                    )}
                </div>
            </div>

            <div className="p-5 space-y-4">
                {/* Tone & strategy */}
                <div className="flex flex-wrap gap-1.5">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 border border-rose-100 uppercase tracking-wider">
                        {content.content_strategy.replace(/_/g, " ")}
                    </span>
                    {content.tone_modifiers.map(t => (
                        <span key={t} className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 uppercase tracking-wider">
                            {t}
                        </span>
                    ))}
                    <code className="text-[10px] font-mono bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                        {content.offer_code}
                    </code>
                </div>

                {/* Channel-specific preview */}
                {content.channel === "email"    && <EmailPreview content={content} />}
                {content.channel === "sms"      && <SmsPreview content={content} />}
                {content.channel === "app"      && <PushPreview content={content} />}
                {(content.channel === "call" || content.channel === "rm_visit") && <CallBriefing content={content} />}

                <p className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Sparkles className="w-2.5 h-2.5" />
                    Generated by DeepSeek V4 Pro via NVIDIA API · {new Date(content.generated_at).toLocaleDateString()}
                </p>
            </div>
        </div>
    );
}
