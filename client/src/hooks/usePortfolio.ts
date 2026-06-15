import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { PortfolioStats } from '@/types';

export function usePortfolio() {
    const [stats, setStats] = useState<PortfolioStats | null>(null);
    const [riskDistribution, setRiskDistribution] = useState<{ tier: string; count: number; percentage: number }[]>([]);
    const [churnTrend, setChurnTrend] = useState<{ week: string; avg_score: number }[]>([]);
    const [signalBreakdown, setSignalBreakdown] = useState<{ signal_type: string; count: number }[]>([]);
    const [topAtRisk, setTopAtRisk] = useState<any[]>([]);
    const [marketSignals, setMarketSignals] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                setIsLoading(true);
                const [
                    statsData,
                    distData,
                    trendData,
                    signalData,
                    topData,
                    marketData
                ] = await Promise.all([
                    api.getPortfolioStats(),
                    api.getRiskDistribution(),
                    api.getChurnTrend(12),
                    api.getSignalBreakdown(),
                    api.getTopAtRisk(10),
                    api.getMarketSignals()
                ]);

                setStats(statsData.data || statsData);
                setRiskDistribution(distData.data || distData || []);
                setChurnTrend(trendData.data || trendData || []);
                setSignalBreakdown(signalData.data || signalData || []);
                setTopAtRisk(topData.data || topData || []);
                setMarketSignals(marketData?.data || marketData || []);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Failed to fetch portfolio data'));
            } finally {
                setIsLoading(false);
            }
        }

        loadData();
    }, []);

    return { stats, riskDistribution, churnTrend, signalBreakdown, topAtRisk, marketSignals, isLoading, error };
}
