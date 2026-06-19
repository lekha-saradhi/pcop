'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Segment, Channel, CreateCustomerInput } from "@/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import ProtectedRoute from "@/components/ProtectedRoute";
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";

type Step = 'form' | 'generating' | 'done';

const GENERATION_STEPS = [
    { key: 'customer', label: 'Creating customer record...' },
    { key: 'accounts', label: 'Setting up accounts...' },
    { key: 'signals', label: 'Fetching customer signals...' },
    { key: 'risk', label: 'Analysing risk profile...' },
    { key: 'transactions', label: 'Building transaction history...' },
];

const SEGMENTS: Segment[] = ['HNW', 'Mass Affluent', 'Mass Market', 'Digital Native'];
const INCOME_BANDS = ['above_25L', '10L_25L', '5L_10L', 'below_5L'];
const CHANNELS: Channel[] = ['email', 'sms', 'app', 'call', 'rm_visit'];
const EMPLOYMENT_TYPES = ['salaried', 'self_employed', 'retired'];

export default function NewCustomerPage() {
    const router = useRouter();
    const [step, setStep] = useState<Step>('form');
    const [completedSteps, setCompletedSteps] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [createdId, setCreatedId] = useState<string | null>(null);

    const [form, setForm] = useState<CreateCustomerInput>({
        full_name: '',
        age: 30,
        city: 'Mumbai',
        segment: 'Mass Market',
        email: '',
        phone_mobile: '',
        employer_name: '',
        employment_type: 'salaried',
        annual_income_band: '5L_10L',
        tenure_years: 0,
        preferred_channel: 'email',
        email_opt_in: true,
        sms_opt_in: true,
        push_opt_in: true,
        call_opt_in: false,
    });

    const update = (field: keyof CreateCustomerInput, value: string | number | boolean) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async () => {
        if (!form.full_name.trim()) { setError('Full name is required'); return; }
        if (!form.email?.trim()) { setError('Email is required'); return; }
        setError(null);
        setStep('generating');

        const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

        for (const s of GENERATION_STEPS) {
            await delay(400 + Math.random() * 400);
            setCompletedSteps(prev => [...prev, s.key]);
        }

        try {
            const res = await api.createCustomer(form);
            const customer = res?.data ?? res;
            setCreatedId(customer.customer_id);
            setStep('done');
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Failed to create customer');
            setStep('form');
            setCompletedSteps([]);
        }
    };

    if (step === 'generating') {
        return (
            <ProtectedRoute>
                <div className="flex items-center justify-center min-h-[60vh]">
                    <Card className="w-full max-w-md">
                        <CardHeader>
                            <CardTitle className="text-center">Setting up your new customer</CardTitle>
                            <CardDescription className="text-center">
                                Please wait while we provision everything
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Progress
                                value={(completedSteps.length / GENERATION_STEPS.length) * 100}
                                className="h-2"
                            />
                            <div className="space-y-3">
                                {GENERATION_STEPS.map(s => (
                                    <div key={s.key} className="flex items-center gap-3 text-sm">
                                        {completedSteps.includes(s.key) ? (
                                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                                        ) : (
                                            <Loader2 className="w-4 h-4 text-slate-400 animate-spin shrink-0" />
                                        )}
                                        <span className={completedSteps.includes(s.key) ? 'text-emerald-700' : 'text-slate-500'}>
                                            {s.label}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </ProtectedRoute>
        );
    }

    if (step === 'done') {
        return (
            <ProtectedRoute>
                <div className="flex items-center justify-center min-h-[60vh]">
                    <Card className="w-full max-w-md text-center">
                        <CardHeader>
                            <div className="flex justify-center mb-2">
                                <CheckCircle2 className="w-12 h-12 text-emerald-500" />
                            </div>
                            <CardTitle>Customer created successfully!</CardTitle>
                            <CardDescription>
                                {createdId} — {form.full_name}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <Button
                                className="w-full"
                                onClick={() => router.push(`/customers/${createdId}`)}
                            >
                                View customer detail
                            </Button>
                            <Button
                                variant="outline"
                                className="w-full"
                                onClick={() => router.push('/customers')}
                            >
                                Back to customer list
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </ProtectedRoute>
        );
    }

    return (
        <ProtectedRoute>
            <div className="flex flex-col gap-6 max-w-2xl">
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="icon" onClick={() => router.push('/customers')}>
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div>
                        <h1 className="text-xl font-semibold text-slate-900">Add New Customer</h1>
                        <p className="text-sm text-slate-500">Enter the customer details below</p>
                    </div>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Personal Information</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-slate-700 mb-1">Full Name *</label>
                            <Input
                                value={form.full_name}
                                onChange={e => update('full_name', e.target.value)}
                                placeholder="e.g. Rajesh Kumar"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
                            <Input
                                type="number"
                                value={form.age}
                                onChange={e => update('age', parseInt(e.target.value) || 0)}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">City</label>
                            <Input
                                value={form.city}
                                onChange={e => update('city', e.target.value)}
                                placeholder="e.g. Mumbai"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Email *</label>
                            <Input
                                type="email"
                                value={form.email}
                                onChange={e => update('email', e.target.value)}
                                placeholder="rajesh@example.com"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                            <Input
                                value={form.phone_mobile || ''}
                                onChange={e => update('phone_mobile', e.target.value)}
                                placeholder="+91-9876543210"
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Banking Profile</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Segment</label>
                            <Select value={form.segment} onValueChange={v => update('segment', v as Segment)}>
                                <SelectTrigger className="h-10 bg-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {SEGMENTS.map(s => (
                                        <SelectItem key={s} value={s}>{s}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Income Band</label>
                            <Select value={form.annual_income_band || ''} onValueChange={v => update('annual_income_band', v)}>
                                <SelectTrigger className="h-10 bg-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {INCOME_BANDS.map(b => (
                                        <SelectItem key={b} value={b}>{b.replace('_', ' ')}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Employer</label>
                            <Input
                                value={form.employer_name || ''}
                                onChange={e => update('employer_name', e.target.value)}
                                placeholder="Company name"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Employment Type</label>
                            <Select value={form.employment_type || ''} onValueChange={v => update('employment_type', v)}>
                                <SelectTrigger className="h-10 bg-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {EMPLOYMENT_TYPES.map(t => (
                                        <SelectItem key={t} value={t}>{t.replace('_', ' ')}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Tenure (years)</label>
                            <Input
                                type="number"
                                value={form.tenure_years || 0}
                                onChange={e => update('tenure_years', parseInt(e.target.value) || 0)}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Preferred Channel</label>
                            <Select value={form.preferred_channel || ''} onValueChange={v => update('preferred_channel', v as Channel)}>
                                <SelectTrigger className="h-10 bg-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {CHANNELS.map(c => (
                                        <SelectItem key={c} value={c}>{c.replace('_', ' ')}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Communication Preferences</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            {[
                                { key: 'email_opt_in' as const, label: 'Email' },
                                { key: 'sms_opt_in' as const, label: 'SMS' },
                                { key: 'push_opt_in' as const, label: 'Push' },
                                { key: 'call_opt_in' as const, label: 'Call' },
                            ].map(opt => (
                                <label key={opt.key} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                        checked={!!form[opt.key]}
                                        onChange={e => update(opt.key, e.target.checked)}
                                    />
                                    <span className="text-sm text-slate-700">{opt.label}</span>
                                </label>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-3 pb-8">
                    <Button variant="outline" onClick={() => router.push('/customers')}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit}>
                        Create Customer
                    </Button>
                </div>
            </div>
        </ProtectedRoute>
    );
}
