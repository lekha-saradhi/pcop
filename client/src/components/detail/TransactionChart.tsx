"use client";

import { useMemo } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { format, parseISO } from "date-fns";

export function TransactionChart({ transactions }: { transactions: any[] }) {
    const chartData = useMemo(() => {
        if (!transactions.length) return [];

        // Group by date (last 60 days strictly)
        const map = new Map();
        transactions.forEach(t => {
            if (!map.has(t.txn_date)) {
                map.set(t.txn_date, { date: t.txn_date, credit: 0, debit: 0 });
            }
            if (t.direction === 'credit') {
                map.get(t.txn_date).credit += parseFloat(t.amount);
            } else {
                map.get(t.txn_date).debit += parseFloat(t.amount);
            }
        });

        return Array.from(map.values())
            .sort((a, b) => a.date.localeCompare(b.date))
            .slice(-60); // Only 60 days
    }, [transactions]);

    return (
        <div className="flex flex-col gap-6">
            <Card className="shadow-sm border-gray-200">
                <CardHeader>
                    <CardTitle className="text-base font-semibold text-slate-900">Transaction Volume (Last 60 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[280px] w-full">
                        {chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{ fontSize: 11, fill: '#64748b' }}
                                        tickFormatter={(val: string) => {
                                            try { return format(parseISO(val), 'MMM d'); } catch { return val; }
                                        }}
                                        dy={10}
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{ fontSize: 11, fill: '#64748b' }}
                                        tickFormatter={(val: number) => `₹${(val / 1000).toFixed(0)}k`}
                                    />
                                    <Tooltip
                                        labelFormatter={(val) => {
                                            try { return format(parseISO(String(val)), 'MMM d, yyyy'); } catch { return String(val); }
                                        }}
                                        formatter={(value, name) => [`₹${Number(value).toLocaleString()}`, String(name).charAt(0).toUpperCase() + String(name).slice(1)]}
                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <Area type="monotone" dataKey="credit" stackId="1" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
                                    <Area type="monotone" dataKey="debit" stackId="2" stroke="#ef4444" fill="#ef4444" fillOpacity={0.2} />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">No transaction data available</div>
                        )}
                    </div>
                </CardContent>
            </Card>

            <Card className="shadow-sm border-gray-200">
                <CardHeader>
                    <CardTitle className="text-base font-semibold text-slate-900">Recent Transactions</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[120px]">Date</TableHead>
                                    <TableHead>Category</TableHead>
                                    <TableHead>Channel</TableHead>
                                    <TableHead>Reference / Merchant</TableHead>
                                    <TableHead className="text-right">Amount</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {transactions.slice(0, 20).map((t, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell className="text-sm text-slate-500">
                                            {t.txn_date}
                                        </TableCell>
                                        <TableCell className="text-sm capitalize">{t.category?.replace('_', ' ')}</TableCell>
                                        <TableCell className="text-sm capitalize text-slate-500">{t.channel}</TableCell>
                                        <TableCell className="text-sm font-medium">
                                            {t.merchant_name || t.payment_ref || '-'}
                                        </TableCell>
                                        <TableCell className={`text-right text-sm font-medium ${t.direction === 'credit' ? 'text-green-600' : 'text-slate-900'}`}>
                                            {t.direction === 'credit' ? '+' : '-'}₹{parseFloat(t.amount).toLocaleString()}
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {transactions.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center text-sm py-6 text-slate-400">No transactions found</TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
