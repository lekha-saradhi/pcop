import os
import logging
import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

_pool = None
DEMO_MODE = os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true"


async def get_pool():
    global _pool
    if _pool is None:
        db_url = os.environ.get("DATABASE_URL", "")
        dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")
        try:
            _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        except Exception:
            logger.warning("ORACLE: DB pool unavailable — demo mode active")
    return _pool


async def get_training_dataset_with_dr_outcomes(
    lookback_days: int = 90,
    min_observation_window: int = 30,
) -> pd.DataFrame:
    """
    Returns training data with DR-adjusted labels for CHRONOS retraining.
    DR-adjusted label: if DR uplift for the customer's stratum was positive,
    use observed outcome as label. If near-zero/negative, downweight the sample.
    """
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    ol.customer_id,
                    oc.outcome_label,
                    CASE WHEN oc.outcome_label = 'churned' THEN 1 ELSE 0 END AS churn_label,
                    COALESCE(ur.dr_uplift, 0) AS dr_uplift,
                    CASE
                        WHEN ur.dr_uplift > 0.02 THEN 1.0
                        WHEN ur.dr_uplift <= 0 THEN 0.3
                        ELSE 0.7
                    END AS sample_weight,
                    oc.churn_score_at_measure,
                    oc.treatability_score_at_send,
                    ol.risk_tier,
                    ol.channel,
                    oc.score_reduction,
                    oc.signals_cleared
                FROM outreach_log ol
                JOIN outcomes oc ON oc.outreach_id = ol.outreach_id
                LEFT JOIN uplift_results ur ON
                    ur.channel = ol.channel AND
                    ur.risk_tier = ol.risk_tier AND
                    ur.observation_window = $2
                WHERE ol.dispatched_at >= NOW() - INTERVAL '$1 days'
                  AND oc.observation_window = $2
            """, lookback_days, min_observation_window)
            return pd.DataFrame([dict(r) for r in rows])
    except Exception:
        if DEMO_MODE:
            import numpy as np
            rng = np.random.default_rng(42)
            n = 500
            dr_uplifts = rng.uniform(-0.05, 0.15, n)
            return pd.DataFrame({
                "customer_id": [f"C-{i:08d}" for i in range(n)],
                "outcome_label": rng.choice(["retained", "partial", "churned"], n, p=[0.5, 0.3, 0.2]),
                "churn_label": rng.integers(0, 2, n),
                "dr_uplift": dr_uplifts,
                "sample_weight": np.clip(dr_uplifts / 0.15, 0.3, 1.0),
                "churn_score_at_measure": rng.uniform(0.2, 0.9, n),
                "treatability_score_at_send": rng.uniform(0.2, 0.9, n),
                "risk_tier": rng.choice(["high", "medium", "watch"], n),
                "channel": rng.choice(["email", "sms", "app"], n),
                "score_reduction": rng.uniform(-0.1, 0.4, n),
                "signals_cleared": rng.choice([True, False], n),
            })
        raise


async def get_causal_net_calibration_signals() -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT model_name, channel, segment, calibration_ok, ate_high, ate_low
                FROM model_calibration_signals
                WHERE model_name = 'causal_net'
                  AND measured_at >= NOW() - INTERVAL '7 days'
                ORDER BY measured_at DESC
            """)
            return [dict(r) for r in rows]
    except Exception:
        return [{"model_name": "causal_net", "calibration_ok": True}] if DEMO_MODE else []


async def get_prompt_versions_with_dr_uplift(channel: str) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    pv.version_id,
                    pv.channel,
                    pp.bandit_alpha,
                    pp.bandit_beta,
                    pp.conversion_rate AS dr_uplift,
                    COUNT(ie.id) AS new_observations_today
                FROM prompt_versions pv
                LEFT JOIN prompt_performance pp ON pp.version_id = pv.version_id
                LEFT JOIN interaction_events ie ON
                    ie.prompt_version_id = pv.version_id AND
                    ie.event_timestamp >= NOW() - INTERVAL '1 day'
                WHERE pv.channel = $1 AND pv.is_active = TRUE
                GROUP BY pv.version_id, pv.channel, pp.bandit_alpha, pp.bandit_beta, pp.conversion_rate
            """, channel)
            return [dict(r) for r in rows]
    except Exception:
        if DEMO_MODE:
            return [
                {"version_id": "v1", "channel": channel, "bandit_alpha": 8.0, "bandit_beta": 4.0, "dr_uplift": 0.08, "new_observations_today": 15},
                {"version_id": "v2", "channel": channel, "bandit_alpha": 5.0, "bandit_beta": 6.0, "dr_uplift": 0.03, "new_observations_today": 12},
            ]
        raise


async def get_ab_variant_outcomes(min_dispatches: int = 100) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    pv.version_id,
                    SUM(CASE WHEN ie.variant = 'A' AND oc.outcome_label = 'retained' THEN 1 ELSE 0 END) AS a_retained,
                    SUM(CASE WHEN ie.variant = 'A' THEN 1 ELSE 0 END) AS a_total,
                    SUM(CASE WHEN ie.variant = 'B' AND oc.outcome_label = 'retained' THEN 1 ELSE 0 END) AS b_retained,
                    SUM(CASE WHEN ie.variant = 'B' THEN 1 ELSE 0 END) AS b_total
                FROM prompt_versions pv
                JOIN interaction_events ie ON ie.prompt_version_id = pv.version_id
                JOIN outcomes oc ON oc.outreach_id = ie.outreach_id
                WHERE pv.channel = 'email'
                  AND ie.variant IS NOT NULL
                GROUP BY pv.version_id
                HAVING SUM(CASE WHEN ie.variant = 'A' THEN 1 ELSE 0 END) >= $1
                   AND SUM(CASE WHEN ie.variant = 'B' THEN 1 ELSE 0 END) >= $1
            """, min_dispatches)
            return [dict(r) for r in rows]
    except Exception:
        return [
            {"version_id": "v1", "a_retained": 45, "a_total": 80, "b_retained": 55, "b_total": 80}
        ] if DEMO_MODE else []


async def get_channel_uplift_by_cell(
    segment: str,
    risk_tier: str,
    life_event_type: str = None,
    content_strategy: str = None,
    primary_signal_type: str = None,
) -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    channel,
                    AVG(dr_uplift) AS dr_uplift,
                    COUNT(*) AS n_samples
                FROM uplift_results
                WHERE segment = $1 AND risk_tier = $2
                GROUP BY channel
                HAVING COUNT(*) >= 5
            """, segment, risk_tier)
            return [dict(r) for r in rows]
    except Exception:
        if DEMO_MODE:
            return [
                {"channel": "email", "dr_uplift": 0.07, "n_samples": 45},
                {"channel": "sms", "dr_uplift": 0.04, "n_samples": 30},
                {"channel": "app", "dr_uplift": 0.09, "n_samples": 38},
            ]
        raise


async def get_distinct_channel_policy_cells() -> list[dict]:
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT segment, risk_tier, content_strategy, primary_signal_type
                FROM uplift_results
                WHERE calculated_at >= NOW() - INTERVAL '7 days'
            """)
            return [dict(r) for r in rows]
    except Exception:
        if DEMO_MODE:
            return [
                {"segment": "mass_affluent", "risk_tier": "high", "content_strategy": "full_retention", "primary_signal_type": "tempo_transaction_freq"},
                {"segment": "mass_affluent", "risk_tier": "medium", "content_strategy": "proactive", "primary_signal_type": None},
            ]
        raise


async def get_top_metric_changes(n: int = 20, lookback_days: int = 7) -> list[dict]:
    """
    Reads top N metric deltas from ClickHouse analytical store.
    Falls back to demo data if ClickHouse unavailable.
    """
    try:
        # ClickHouse connection would go here
        # For now this is a demo-only path
        raise RuntimeError("ClickHouse not configured")
    except Exception:
        if DEMO_MODE:
            return [
                {"metric_name": "argus_alarm_count", "current_value": 847, "prior_value": 612, "delta_pct": 38.4, "severity": "high", "segment": "mass_affluent", "channel": "all", "affected_customers": 847},
                {"metric_name": "dr_uplift_email", "current_value": 0.082, "prior_value": 0.065, "delta_pct": 26.2, "severity": "info", "segment": "all", "channel": "email", "affected_customers": None},
                {"metric_name": "sentinel_failure_rate", "current_value": 0.031, "prior_value": 0.018, "delta_pct": 72.2, "severity": "high", "segment": "all", "channel": "sms", "affected_customers": 143},
                {"metric_name": "causal_net_calibration_gap", "current_value": 0.004, "prior_value": 0.021, "delta_pct": -81.0, "severity": "info", "segment": "mass_affluent", "channel": "all", "affected_customers": None},
                {"metric_name": "holdout_rescue_count", "current_value": 12, "prior_value": 4, "delta_pct": 200.0, "severity": "medium", "segment": "all", "channel": "all", "affected_customers": 12},
            ][:n]
        raise
