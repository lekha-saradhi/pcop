import { ReactNode } from "react";

interface StatCardProps {
    title: string;
    value: string | number;
    subtitle: string;
    icon: ReactNode;
    accent?: "default" | "red" | "orange" | "blue" | "emerald";
    valueClassName?: string;
}

const ACCENT: Record<string, { border: string; icon: string; badge: string }> = {
    default:  { border: "border-l-slate-300",  icon: "bg-slate-100 text-slate-500",    badge: "" },
    red:      { border: "border-l-red-400",     icon: "bg-red-50 text-red-600",         badge: "text-red-600" },
    orange:   { border: "border-l-orange-400",  icon: "bg-orange-50 text-orange-600",   badge: "text-orange-600" },
    blue:     { border: "border-l-blue-500",    icon: "bg-blue-50 text-blue-600",       badge: "text-blue-600" },
    emerald:  { border: "border-l-emerald-400", icon: "bg-emerald-50 text-emerald-600", badge: "text-emerald-600" },
};

export function StatCard({ title, value, subtitle, icon, accent = "default", valueClassName = "" }: StatCardProps) {
    const a = ACCENT[accent];
    return (
        <div className={`bg-white rounded-xl border border-slate-200 border-l-4 ${a.border} p-5 flex flex-col gap-3 shadow-sm`}>
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${a.icon}`}>
                    {icon}
                </div>
            </div>
            <div>
                <div className={`text-3xl font-bold text-slate-900 leading-none ${valueClassName}`}>{value}</div>
                <p className="text-xs text-slate-400 mt-1.5">{subtitle}</p>
            </div>
        </div>
    );
}
