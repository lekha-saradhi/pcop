"use client";

import { Mail, MessageSquare, Smartphone, Phone, ShieldCheck, ShieldX, User, Building2, CreditCard, MapPin, Briefcase, AlertTriangle, CheckCircle2, XCircle, Clock, BadgeInfo } from "lucide-react";

interface Customer {
    customer_id: string;
    full_name: string;
    age: number;
    city: string;
    segment: string;
    tenure_years: number;
    preferred_channel: string;
    email: string;
    phone_mobile: string;
    employer_name: string;
    employment_type: string;
    annual_income_band: string;
    email_opt_in: boolean;
    sms_opt_in: boolean;
    push_opt_in: boolean;
    call_opt_in: boolean;
    kyc_status: string;
    relationship_manager_id: string;
    churn_score: number;
    risk_tier: string;
}

interface Account {
    account_id: string;
    account_type: string;
    product_code: string;
    balance: number;
    status: string;
    interest_rate?: number;
    credit_limit?: number;
    opened_date: string;
}

interface Enrichment {
    linkedin_employer?: string;
    linkedin_title?: string;
    credit_score?: number;
    credit_score_band?: string;
    competitor_proximity?: number;
    news_risk_flag?: boolean;
    news_summary?: string;
}

interface CompliancePanelProps {
    customer: Customer;
    accounts?: Account[];
    enrichment?: Enrichment | null;
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
    return (
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
            {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {label}
        </div>
    );
}

function Row({ icon: Icon, label, value, muted }: { icon: any; label: string; value: string | React.ReactNode; muted?: boolean }) {
    return (
        <div className="flex items-start gap-2.5 py-2 border-b border-slate-50 last:border-0">
            <Icon className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
            <span className="text-xs text-slate-400 w-28 shrink-0">{label}</span>
            <span className={`text-xs font-medium ${muted ? 'text-slate-400 italic' : 'text-slate-800'} flex-1`}>{value}</span>
        </div>
    );
}

const INCOME_LABEL: Record<string, string> = {
    above_25L: '> ₹25L / yr',
    between_10L_25L: '₹10L – ₹25L / yr',
    between_5L_10L: '₹5L – ₹10L / yr',
    below_5L: '< ₹5L / yr',
};

const CREDIT_BAND_COLOR: Record<string, string> = {
    excellent: 'text-emerald-600',
    good: 'text-blue-600',
    fair: 'text-amber-600',
    poor: 'text-red-600',
};

export function CompliancePanel({ customer, accounts = [], enrichment }: CompliancePanelProps) {
    const channels = [
        { key: 'email',    label: 'Email',   icon: Mail,           enabled: customer.email_opt_in },
        { key: 'sms',      label: 'SMS',     icon: MessageSquare,  enabled: customer.sms_opt_in },
        { key: 'push',     label: 'Push',    icon: Smartphone,     enabled: customer.push_opt_in },
        { key: 'call',     label: 'Call/RM', icon: Phone,          enabled: customer.call_opt_in },
    ];

    const kycOk      = customer.kyc_status === 'verified';
    const activeAccts = accounts.filter(a => a.status === 'active');
    const totalBalance = activeAccts.reduce((s, a) => s + (a.balance || 0), 0);
    const preferredCh = channels.find(c => c.key === customer.preferred_channel || (customer.preferred_channel === 'in_app' && c.key === 'push'));

    return (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-slate-500" />
                    <span className="text-sm font-bold text-slate-800">Compliance & Channel Eligibility</span>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider flex items-center gap-1 ${kycOk ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
                    {kycOk ? <CheckCircle2 className="w-2.5 h-2.5" /> : <AlertTriangle className="w-2.5 h-2.5" />}
                    KYC {customer.kyc_status}
                </span>
            </div>

            <div className="p-4 space-y-5">

                {/* Channel opt-in grid */}
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Outreach Channel Eligibility</p>
                    <div className="grid grid-cols-2 gap-2">
                        {channels.map(ch => {
                            const Icon = ch.icon;
                            const isPref = customer.preferred_channel === ch.key || (customer.preferred_channel === 'in_app' && ch.key === 'push');
                            return (
                                <div key={ch.key} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold ${ch.enabled ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-slate-50 border-slate-200 text-slate-400 line-through'}`}>
                                    <Icon className="w-3.5 h-3.5 shrink-0" />
                                    {ch.label}
                                    {isPref && ch.enabled && (
                                        <span className="ml-auto text-[9px] font-bold bg-emerald-600 text-white px-1 py-0.5 rounded">PREF</span>
                                    )}
                                    {!ch.enabled && (
                                        <XCircle className="ml-auto w-3 h-3 text-slate-300" />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    {!channels.some(c => c.enabled) && (
                        <div className="mt-2 flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                            <ShieldX className="w-3.5 h-3.5 shrink-0" />
                            No outreach channels enabled — contact suppressed
                        </div>
                    )}
                </div>

                {/* Contact details */}
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Contact Details</p>
                    <div className="bg-slate-50 rounded-lg px-3 py-1">
                        <Row icon={Mail}    label="Email"    value={customer.email || '—'} />
                        <Row icon={Phone}   label="Mobile"   value={customer.phone_mobile || '—'} />
                        <Row icon={MapPin}  label="City"     value={customer.city} />
                        <Row icon={User}    label="RM"       value={customer.relationship_manager_id} />
                    </div>
                </div>

                {/* Profile */}
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Customer Profile</p>
                    <div className="bg-slate-50 rounded-lg px-3 py-1">
                        <Row icon={Briefcase} label="Employer"   value={customer.employer_name || (enrichment?.linkedin_employer ?? '—')} />
                        <Row icon={BadgeInfo} label="Title"      value={enrichment?.linkedin_title ?? '—'} muted={!enrichment?.linkedin_title} />
                        <Row icon={Briefcase} label="Employment" value={customer.employment_type.replace(/_/g, ' ')} />
                        <Row icon={Building2} label="Income"     value={INCOME_LABEL[customer.annual_income_band] ?? customer.annual_income_band} />
                        <Row icon={Clock}     label="Tenure"     value={`${customer.tenure_years} years`} />
                    </div>
                </div>

                {/* Accounts */}
                {activeAccts.length > 0 && (
                    <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                            Active Accounts
                            <span className="ml-2 font-mono text-slate-500 normal-case tracking-normal">
                                Total ₹{totalBalance.toLocaleString('en-IN')}
                            </span>
                        </p>
                        <div className="space-y-1.5">
                            {activeAccts.map(a => (
                                <div key={a.account_id} className="flex items-center justify-between px-3 py-2 bg-slate-50 rounded-lg border border-slate-100 text-xs">
                                    <div className="flex items-center gap-2">
                                        <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                                        <span className="font-semibold text-slate-700 capitalize">{a.account_type.replace(/_/g, ' ')}</span>
                                        <code className="text-[10px] text-slate-400 bg-slate-100 px-1 rounded">{a.product_code}</code>
                                    </div>
                                    <span className="font-bold text-slate-800">₹{Number(a.balance).toLocaleString('en-IN')}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Enrichment / external signals */}
                {enrichment && (
                    <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">External Intelligence</p>
                        <div className="bg-slate-50 rounded-lg px-3 py-1">
                            {enrichment.credit_score != null && (
                                <Row
                                    icon={ShieldCheck}
                                    label="Credit Score"
                                    value={
                                        <span>
                                            <span className="font-bold">{enrichment.credit_score}</span>
                                            {enrichment.credit_score_band && (
                                                <span className={`ml-1.5 text-[10px] font-bold uppercase ${CREDIT_BAND_COLOR[enrichment.credit_score_band] ?? 'text-slate-500'}`}>
                                                    {enrichment.credit_score_band}
                                                </span>
                                            )}
                                        </span>
                                    }
                                />
                            )}
                            {enrichment.competitor_proximity != null && (
                                <Row
                                    icon={AlertTriangle}
                                    label="Competitor"
                                    value={
                                        <span className={enrichment.competitor_proximity <= 2 ? 'text-red-600 font-bold' : 'text-slate-700'}>
                                            {enrichment.competitor_proximity} branch{enrichment.competitor_proximity !== 1 ? 'es' : ''} nearby
                                        </span>
                                    }
                                />
                            )}
                            {enrichment.news_summary && (
                                <Row icon={BadgeInfo} label="News Signal" value={enrichment.news_summary} muted={!enrichment.news_risk_flag} />
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
