import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { V2Score, ActionPlan, HeraldContent } from '@/types';

interface V2CustomerData {
    score: V2Score | null;
    actionPlan: ActionPlan | null;
    content: HeraldContent | null;
    loading: boolean;
    error: Error | null;
}

export function useV2CustomerData(customerId: string | undefined): V2CustomerData {
    const [score, setScore] = useState<V2Score | null>(null);
    const [actionPlan, setActionPlan] = useState<ActionPlan | null>(null);
    const [content, setContent] = useState<HeraldContent | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        if (!customerId) {
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        Promise.all([
            api.getV2Score(customerId).catch(() => null),
            api.getV2ActionPlan(customerId).catch(() => null),
            api.getV2Content(customerId).catch(() => null),
        ]).then(([scoreData, planData, contentData]) => {
            setScore(scoreData?.data ?? scoreData);
            setActionPlan(planData?.data ?? planData);
            setContent(contentData?.data ?? contentData);
        }).catch(err => {
            setError(err instanceof Error ? err : new Error('Failed to load v2 data'));
        }).finally(() => {
            setLoading(false);
        });
    }, [customerId]);

    return { score, actionPlan, content, loading, error };
}
