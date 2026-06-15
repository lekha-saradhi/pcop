import os
import logging
import asyncpg
import pandas as pd
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

_pool = None
DEMO_MODE = os.environ.get("VERDICT_DEMO_MODE", "true").lower() == "true"


async def get_pool():
    global _pool
    if _pool is None:
        db_url = os.environ.get("DATABASE_URL", "")
        dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")
        try:
            _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        except Exception:
            logger.warning("VERDICT: DB pool unavailable — demo mode active")
    return _pool


async def get_outreach_context(outreach_id: int) -> dict:
    """Enriches interaction events with HERALD context from content_store + outreach_log."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    ol.customer_id,
                    ol.channel,
                    ol.risk_tier,
                    ol.final_score,
                    cs.content_store_id,
                    cs.prompt_version_id,
                    cs.content_strategy,
                    cs.ab_variant_content IS NOT NULL AS has_ab_variant,
                    ol.treatability_score,
                    ol.life_events_detected AS life_events
                FROM outreach_log ol
                LEFT JOIN content_store cs ON cs.outreach_id = ol.outreach_id
                WHERE ol.outreach_id = $1
            """, outreach_id)
            return dict(row) if row else {}
    except Exception:
        if DEMO_MODE:
            return {
                "customer_id": f"C-{outreach_id:08d}",
                "channel": "email",
                "risk_tier": "high",
                "final_score": 0.75,
                "content_store_id": outreach_id,
                "prompt_version": "v1",
                "content_strategy": "full_retention",
                "has_ab_variant": False,
                "treatability_score": 0.6,
                "life_events": ["job_change"],
            }
        raise


async def get_dispatched_customers_for_window(target_send_date: date) -> list[dict]:
    """Returns all customers whose outreach was dispatched on target_send_date."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    ol.customer_id,
                    ol.outreach_id,
                    ol.dispatched_at,
                    ol.holdout_group,
                    ol.treatability_score,
                    cs.final_score,
                    tb.baselines AS argus_baseline
                FROM outreach_log ol
                LEFT JOIN churn_scores cs ON cs.customer_id = ol.customer_id
                LEFT JOIN tempo_baselines tb ON tb.customer_id = ol.customer_id
                WHERE ol.dispatched_at::date = $1
                  AND ol.status IN ('dispatched', 'holdout')
            """, target_send_date)
            return [dict(r) for r in rows]
    except Exception:
        if DEMO_MODE:
            return [
                {
                    "customer_id": f"C-{i:08d}",
                    "outreach_id": i,
                    "dispatched_at": datetime.combine(target_send_date, datetime.min.time()),
                    "holdout_group": i % 7 == 0,
                    "treatability_score": 0.6,
                    "final_score": 0.72,
                    "argus_baseline": {"transaction_frequency_mu": 15, "churn_score_at_send": 0.72},
                }
                for i in range(1, 6)
            ]
        raise


async def get_transaction_volume(customer_id: str, start: date, end: date) -> float:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT COUNT(*) AS txn_count
                FROM transactions
                WHERE customer_id = $1
                  AND transaction_date BETWEEN $2 AND $3
            """, customer_id, start, end)
            return float(row["txn_count"]) if row else 0.0
    except Exception:
        return 14.0 if DEMO_MODE else 0.0


async def get_engagement_score(customer_id: str, as_of: date) -> dict:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT score, delta_vs_baseline
                FROM engagement_scores
                WHERE customer_id = $1
                ORDER BY scored_at DESC
                LIMIT 1
            """, customer_id)
            return dict(row) if row else {"score": 0.5, "delta_vs_baseline": 0.0}
    except Exception:
        return {"score": 0.65, "delta_vs_baseline": 0.05} if DEMO_MODE else {}


async def get_current_churn_score(customer_id: str) -> dict:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT final_score, risk_tier, treatability_score
                FROM churn_scores
                WHERE customer_id = $1
                ORDER BY scored_at DESC
                LIMIT 1
            """, customer_id)
            return dict(row) if row else {}
    except Exception:
        return {"final_score": 0.35, "risk_tier": "medium", "treatability_score": 0.55} if DEMO_MODE else {}


async def get_active_signals(customer_id: str) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT signal_type, detected, confidence
                FROM signal_results
                WHERE customer_id = $1 AND detected = TRUE AND resolved_at IS NULL
                ORDER BY detected_at DESC
            """, customer_id)
            return [dict(r) for r in rows]
    except Exception:
        return [] if DEMO_MODE else []


async def get_product_closures(customer_id: str, start: date, end: date) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT account_id, account_type, closed_at
                FROM accounts
                WHERE customer_id = $1
                  AND status = 'closed'
                  AND closed_at::date BETWEEN $2 AND $3
            """, customer_id, start, end)
            return [dict(r) for r in rows]
    except Exception:
        return [] if DEMO_MODE else []


async def get_balance_change(customer_id: str, start: date, end: date) -> float:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    SUM(CASE WHEN txn_date::date = $3 THEN amount ELSE 0 END) -
                    SUM(CASE WHEN txn_date::date = $2 THEN amount ELSE 0 END) AS balance_delta
                FROM transactions
                WHERE customer_id = $1
                  AND txn_date::date IN ($2, $3)
            """, customer_id, start, end)
            return float(row["balance_delta"] or 0) if row else 0.0
    except Exception:
        return 1200.0 if DEMO_MODE else 0.0


async def get_attribution_dataset(
    campaign_id: str = None,
    channel: str = None,
    segment: str = None,
    risk_tier: str = None,
    observation_window: int = 30,
    content_strategy: str = None,
    prompt_version_id: str = None,
) -> pd.DataFrame:
    """Returns treatment + holdout data for DR uplift estimation."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            conditions = ["oc.observation_window = $1"]
            params = [observation_window]
            idx = 2
            if channel:
                conditions.append(f"ol.channel = ${idx}")
                params.append(channel)
                idx += 1
            if segment:
                conditions.append(f"c.segment = ${idx}")
                params.append(segment)
                idx += 1
            if risk_tier:
                conditions.append(f"ol.risk_tier = ${idx}")
                params.append(risk_tier)
                idx += 1
            if content_strategy:
                conditions.append(f"cs.content_strategy = ${idx}")
                params.append(content_strategy)
                idx += 1
            if prompt_version_id:
                conditions.append(f"cs.prompt_version_id = ${idx}")
                params.append(prompt_version_id)
                idx += 1

            where = " AND ".join(conditions)
            rows = await conn.fetch(f"""
                SELECT
                    ol.customer_id,
                    CASE WHEN ol.holdout_group THEN 0 ELSE 1 END AS treatment,
                    oc.outcome_label,
                    oc.churn_score_at_measure,
                    oc.score_reduction,
                    oc.treatability_score_at_send,
                    cs2.final_score AS final_score_at_send,
                    c.tenure_years,
                    c.num_active_products,
                    c.digital_ratio,
                    c.complaint_count_90d,
                    c.recency_days,
                    c.frequency_monthly,
                    c.monetary_avg,
                    oc.active_signal_count,
                    0 AS life_event_count_at_send,
                    cs.content_strategy
                FROM outreach_log ol
                JOIN outcomes oc ON oc.outreach_id = ol.outreach_id
                JOIN customers c ON c.customer_id = ol.customer_id
                LEFT JOIN content_store cs ON cs.outreach_id = ol.outreach_id
                LEFT JOIN churn_scores cs2 ON cs2.customer_id = ol.customer_id
                WHERE {where}
            """, *params)
            return pd.DataFrame([dict(r) for r in rows])
    except Exception:
        if DEMO_MODE:
            import numpy as np
            rng = np.random.default_rng(42)
            n = 120
            return pd.DataFrame({
                "customer_id": [f"C-{i:08d}" for i in range(n)],
                "treatment": rng.integers(0, 2, n),
                "outcome_label": rng.choice(["retained", "partial", "churned", "unresponsive"], n, p=[0.5, 0.3, 0.1, 0.1]),
                "churn_score_at_measure": rng.uniform(0.2, 0.8, n),
                "score_reduction": rng.uniform(-0.1, 0.3, n),
                "treatability_score_at_send": rng.uniform(0.2, 0.9, n),
                "final_score_at_send": rng.uniform(0.5, 0.95, n),
                "tenure_years": rng.uniform(0.5, 15, n),
                "num_active_products": rng.integers(1, 6, n),
                "digital_ratio": rng.uniform(0.1, 1.0, n),
                "complaint_count_90d": rng.integers(0, 5, n),
                "recency_days": rng.integers(1, 90, n),
                "frequency_monthly": rng.uniform(2, 30, n),
                "monetary_avg": rng.uniform(500, 50000, n),
                "active_signal_count": rng.integers(0, 4, n),
                "life_event_count_at_send": rng.integers(0, 3, n),
                "content_strategy": rng.choice(["full_retention", "graceful_retention", "proactive"], n),
            })
        raise


async def get_active_prompt_versions(channel: str) -> list[str]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT version_id FROM prompt_versions
                WHERE channel = $1 AND is_active = TRUE
            """, channel)
            return [r["version_id"] for r in rows]
    except Exception:
        return ["v1", "v2"] if DEMO_MODE else []


async def get_original_alarm_signals(outreach_id: int) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT signal_type, detected, confidence
                FROM signal_results sr
                JOIN outreach_log ol ON ol.customer_id = sr.customer_id
                WHERE ol.outreach_id = $1
                  AND sr.detected_at <= ol.dispatched_at
            """, outreach_id)
            return [dict(r) for r in rows]
    except Exception:
        return [{"signal_type": "tempo_transaction_freq", "detected": True, "confidence": 0.88}] if DEMO_MODE else []


async def get_tempo_baselines(customer_id: str, signal_types: list[str]) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT signal_type, update_status, baseline_mu, baseline_sigma
                FROM tempo_baselines
                WHERE customer_id = $1 AND signal_type = ANY($2)
            """, customer_id, signal_types)
            return [dict(r) for r in rows]
    except Exception:
        return [{"signal_type": t, "update_status": "normal"} for t in signal_types] if DEMO_MODE else []


async def get_active_holdouts() -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT customer_id, campaign_id, risk_tier_at_entry, entered_holdout_at
                FROM holdout_registry
                WHERE exited_holdout_at IS NULL
            """)
            return [dict(r) for r in rows]
    except Exception:
        return [] if DEMO_MODE else []


async def update_prompt_version_uplift(version_id: str, dr_uplift: float):
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO prompt_performance (version_id, conversion_rate)
                VALUES ($1, $2)
                ON CONFLICT (version_id) DO UPDATE
                SET conversion_rate = $2, updated_at = NOW()
            """, version_id, dr_uplift)
    except Exception:
        if DEMO_MODE:
            logger.info(f"DEMO: Would update prompt {version_id} uplift → {dr_uplift:.4f}")
        else:
            raise
