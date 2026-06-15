"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Building2, MapPin, Briefcase, Phone, Mail } from "lucide-react";
import { Customer } from "@/types";
import { RiskBadge } from "@/components/customers/RiskBadge";
import { Badge } from "@/components/ui/badge";

export function CustomerHeader({ customer }: { customer: Customer }) {
    const router = useRouter();

    return (
        <div className="flex flex-col gap-4 mb-6">
            <button
                onClick={() => router.push('/customers')}
                className="flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 w-fit transition-colors"
            >
                <ArrowLeft className="w-4 h-4 mr-1.5" />
                Back to Customers
            </button>

            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div>
                    <div className="flex items-end gap-3 mb-2">
                        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{customer.full_name}</h1>
                        <span className="text-lg text-slate-400 font-mono mb-0.5">{customer.customer_id}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                        <span className="flex items-center"><MapPin className="w-4 h-4 mr-1" />{customer.city}</span>
                        <span className="flex items-center"><Building2 className="w-4 h-4 mr-1" />{customer.employer_name || 'Unknown'}</span>
                        <span className="flex items-center"><Briefcase className="w-4 h-4 mr-1" />{customer.tenure_years} Years Tenure</span>
                        <Badge variant="secondary" className="font-normal text-xs">{customer.segment}</Badge>
                    </div>
                </div>

                <div className="flex flex-col items-end gap-2 bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-center gap-3 w-full justify-between sm:justify-end">
                        <span className="text-sm font-medium text-slate-500">Churn Risk</span>
                        <span className="text-2xl font-bold leading-none">{Math.round(customer.churn_score * 100)}%</span>
                        <RiskBadge tier={customer.risk_tier} />
                    </div>
                    <div className="flex gap-2 w-full justify-between sm:justify-end items-center mt-1">
                        <span className="text-xs text-slate-500">Preferred Channel:</span>
                        <Badge variant="outline" className="text-xs font-medium capitalize bg-slate-50">
                            {customer.preferred_channel.replace('_', ' ')}
                        </Badge>
                    </div>
                </div>
            </div>
        </div>
    );
}
