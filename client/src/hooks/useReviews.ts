"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { ReviewCase, ReviewItem, ReviewStats, ReviewOfficer, ReviewActionType, ReviewStatus, ReviewType, ReviewPriority } from "@/types";

interface ReviewFilters {
    status?: string;
    type?: string;
    priority?: string;
    page?: number;
    limit?: number;
}

function tierToPriority(tier: string): ReviewPriority {
    if (tier === 'PRIORITY') return 'critical';
    if (tier === 'ESCALATE') return 'high';
    if (tier === 'STANDARD') return 'medium';
    return 'low';
}

function enrichReview(r: ReviewItem): ReviewCase {
    const actions = r.reviewer ? [{
        id:             `${r.id}-1`,
        action:         r.status as ReviewActionType,
        comment:        r.notes ?? undefined,
        timestamp:      r.reviewed_at ?? r.created_at,
        officerName:    r.reviewer,
        previousStatus: 'pending' as ReviewStatus,
        newStatus:      r.status as ReviewStatus,
    }] : [];
    return {
        ...r,
        status:      r.status as ReviewStatus,
        type:        'score_alert' as ReviewType,
        title:       `Risk Alert — ${r.full_name}`,
        description: `${r.risk_tier} risk customer flagged for ${r.action.replace(/_/g, ' ')} intervention.`,
        priority:    tierToPriority(r.risk_tier),
        createdAt:   r.created_at,
        createdBy:   'CHRONOS (system)',
        context:     {},
        actions,
    };
}

export function useReviews(filters: ReviewFilters = {}) {
    const [cases, setCases] = useState<ReviewCase[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetch = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.getReviews(filters as Record<string, string | number | undefined>);
            setCases((res.reviews || []).map(enrichReview));
            setTotal(res.total ?? 0);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load reviews");
        } finally {
            setLoading(false);
        }
    }, [JSON.stringify(filters)]);

    useEffect(() => { fetch(); }, [fetch]);

    return { cases, total, loading, error, refetch: fetch };
}

export function useReviewDetail(id: string) {
    const [review, setReview] = useState<ReviewCase | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetch = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        setError(null);
        try {
            const res = await api.getReviewById(id);
            const raw: ReviewItem = res.review ?? res;
            setReview(enrichReview(raw));
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load review");
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => { fetch(); }, [fetch]);

    return { review, loading, error, refetch: fetch };
}

export function useReviewStats(options?: { skip?: boolean }) {
    const [stats, setStats] = useState<ReviewStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (options?.skip) { setLoading(false); return; }
        api.getReviewStats()
            .then((res) => setStats(res.data ?? res))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [options?.skip]);

    return { stats, loading };
}

export function useReviewOfficers() {
    const [officers, setOfficers] = useState<ReviewOfficer[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getReviewOfficers()
            .then((res) => setOfficers(res.data ?? res.officers ?? []))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    return { officers, loading };
}
