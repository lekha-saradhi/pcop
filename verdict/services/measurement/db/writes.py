import os
import logging
import asyncpg
from .reads import get_pool

logger = logging.getLogger(__name__)
DEMO_MODE = os.environ.get("VERDICT_DEMO_MODE", "true").lower() == "true"


async def write_interaction_event(event: dict) -> int:
    """Inserts an enriched interaction event. Returns event row id."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO interaction_events (
                    event_id, outreach_id, customer_id, channel, event_type,
                    event_timestamp, duration_seconds, outcome, link_url, variant,
                    content_store_id, prompt_version_id, content_strategy,
                    ab_variant, life_events_at_send, risk_tier_at_send,
                    final_score_at_send, treatability_score_at_send
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING id
            """,
                event.get("event_id"),
                event.get("outreach_id"),
                event.get("customer_id"),
                event.get("channel"),
                event.get("event_type"),
                event.get("event_timestamp"),
                event.get("duration_seconds"),
                event.get("outcome"),
                event.get("link_url"),
                event.get("variant"),
                event.get("content_store_id"),
                event.get("prompt_version_id"),
                event.get("content_strategy"),
                event.get("ab_variant"),
                event.get("life_events_at_send"),
                event.get("risk_tier_at_send"),
                event.get("final_score_at_send"),
                event.get("treatability_score_at_send"),
            )
            return row["id"] if row else 0
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: write_interaction_event "
                f"outreach={event.get('outreach_id')} "
                f"type={event.get('event_type')}"
            )
            return 0
        raise


async def write_outcome(data: dict):
    """Upserts a customer outcome record for a given observation window."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO outcomes (
                    customer_id, outreach_id, holdout_group, observation_window,
                    outcome_label, txn_volume_change, engagement_change,
                    balance_change, products_closed, churn_score_at_measure,
                    score_reduction, signals_cleared, active_signal_count, measured_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (outreach_id, observation_window) DO UPDATE SET
                    outcome_label = EXCLUDED.outcome_label,
                    churn_score_at_measure = EXCLUDED.churn_score_at_measure,
                    score_reduction = EXCLUDED.score_reduction,
                    signals_cleared = EXCLUDED.signals_cleared,
                    measured_at = EXCLUDED.measured_at
            """,
                data["customer_id"], data["outreach_id"], data["holdout_group"],
                data["observation_window"], data["outcome_label"],
                data["txn_volume_change"], data["engagement_change"],
                data["balance_change"], data["products_closed"],
                data.get("churn_score_at_measure"), data["score_reduction"],
                data["signals_cleared"], data["active_signal_count"],
                data["measured_at"],
            )
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: write_outcome customer={data['customer_id']} "
                f"window={data['observation_window']} label={data['outcome_label']}"
            )
        else:
            raise


async def write_uplift_results(data: dict):
    """Inserts a DR uplift result record."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO uplift_results (
                    campaign_id, channel, segment, risk_tier, observation_window,
                    treatment_n, holdout_n, treatment_retention_rate, holdout_retention_rate,
                    naive_uplift, dr_uplift, dr_uplift_se, overestimation_bias,
                    ate_high_treatability, ate_low_treatability,
                    estimator, content_strategy, prompt_version_id, calculated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
            """,
                data["campaign_id"], data["channel"], data["segment"],
                data["risk_tier"], data["observation_window"],
                data["treatment_n"], data["holdout_n"],
                data["treatment_retention_rate"], data["holdout_retention_rate"],
                data["naive_uplift"], data["dr_uplift"], data["dr_uplift_se"],
                data["overestimation_bias"], data.get("ate_high_treatability"),
                data.get("ate_low_treatability"), data.get("estimator", "DR-Learner"),
                data.get("content_strategy"), data.get("prompt_version_id"),
                data["calculated_at"],
            )
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: write_uplift_results "
                f"campaign={data['campaign_id']} channel={data['channel']} "
                f"dr_uplift={data.get('dr_uplift', 0):.4f}"
            )
        else:
            raise


async def write_holdout_registry(data: dict):
    """Registers a customer in the holdout group."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO holdout_registry (
                    customer_id, campaign_id, risk_tier_at_entry,
                    risk_score_at_entry, entered_holdout_at
                ) VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (customer_id, campaign_id) DO NOTHING
            """,
                data["customer_id"], data["campaign_id"],
                data.get("risk_tier_at_entry"), data.get("risk_score_at_entry"),
                data["entered_holdout_at"],
            )
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: write_holdout_registry "
                f"customer={data['customer_id']} campaign={data['campaign_id']}"
            )
        else:
            raise


async def rescue_holdout_customer(customer_id: str, exit_reason: str):
    """Marks a holdout customer as rescued (exited holdout)."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE holdout_registry
                SET exited_holdout_at = NOW(), exit_reason = $2
                WHERE customer_id = $1 AND exited_holdout_at IS NULL
            """, customer_id, exit_reason)
    except Exception:
        if DEMO_MODE:
            logger.info(f"DEMO: rescue_holdout customer={customer_id} reason={exit_reason}")
        else:
            raise


async def write_model_calibration_signal(data: dict):
    """Records a CAUSAL-NET calibration check result for Layer 7 RETRAIN."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_calibration_signals (
                    model_name, channel, segment, calibration_ok, ate_high, ate_low, n_samples
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
                data.get("model_name", "causal_net"),
                data.get("channel"), data.get("segment"),
                data["calibration_ok"],
                data.get("ate_high"), data.get("ate_low"),
                data.get("n_samples"),
            )
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: model_calibration_signal "
                f"channel={data.get('channel')} calibrated={data['calibration_ok']}"
            )
        else:
            raise
