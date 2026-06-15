import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export function useCustomerDetail(id: string) {
    const [snapshot, setSnapshot] = useState<any>(null);
    const [signals, setSignals] = useState<any[]>([]);
    const [transactions, setTransactions] = useState<any[]>([]);
    const [insights, setInsights] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        async function loadDetail() {
            try {
                setIsLoading(true);
                const [snapData, sigData, txData, insightData] = await Promise.all([
                    api.getCustomerById(id),
                    api.getCustomerSignals(id),
                    api.getCustomerTransactions(id).catch(() => []), 
                    api.getCustomerInsights(id).catch(() => null)
                ]);

                setSnapshot(snapData?.data || snapData);
                setSignals(sigData?.data || sigData || []);
                setInsights(insightData?.data || insightData);

                // The demoServer returns { status, count, data } for transactions
                setTransactions(txData?.data || txData || []);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Failed to fetch customer detail'));
            } finally {
                setIsLoading(false);
            }
        }

        if (id) {
            loadDetail();
        }
    }, [id]);

    return { snapshot, signals, transactions, insights, isLoading, error };
}
