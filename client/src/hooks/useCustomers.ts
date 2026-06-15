import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Customer } from '@/types';

export function useCustomers(filters?: { segment?: string; risk_tier?: string; city?: string; search?: string }) {
    const [customers, setCustomers] = useState<Customer[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        async function loadCustomers() {
            try {
                setIsLoading(true);
                // We fetch all 20 for the demo and do client-side filtering since the PRD mentioned client-side filtering 
                // for search, but backend limits to 20 by default (page 1, limit 20 matches all demo data).
                const data = await api.getCustomers({ ...filters, limit: 100 });
                setCustomers(data.data || []);
                setTotal(data.total || 0);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Failed to fetch customers'));
            } finally {
                setIsLoading(false);
            }
        }

        loadCustomers();
    }, [filters?.segment, filters?.risk_tier, filters?.city, filters?.search]);

    return { customers, total, isLoading, error };
}
