import os
import logging
from .reads import get_pool

logger = logging.getLogger(__name__)
DEMO_MODE = os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true"


async def update_bandit_params(
    version_id: str,
    alpha_increment: int,
    beta_increment: int,
    conversion_rate: float,
):
    """Updates Thompson sampling bandit parameters for a prompt version."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO prompt_performance (version_id, bandit_alpha, bandit_beta, conversion_rate)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (version_id) DO UPDATE SET
                    bandit_alpha = prompt_performance.bandit_alpha + $2,
                    bandit_beta  = prompt_performance.bandit_beta  + $3,
                    conversion_rate = $4,
                    updated_at = NOW()
            """, version_id, float(alpha_increment), float(beta_increment), conversion_rate)
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: update_bandit {version_id} "
                f"alpha+={alpha_increment} beta+={beta_increment} "
                f"dr_uplift={conversion_rate:.4f}"
            )
        else:
            raise


async def promote_prompt_variant(version_id: str, winner: str):
    """Marks the winning A/B variant as primary in prompt_versions."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE prompt_versions
                SET tone_instructions = tone_instructions || ' [AB_WINNER=' || $2 || ']',
                    is_active = TRUE
                WHERE version_id = $1
            """, version_id, winner)
    except Exception:
        if DEMO_MODE:
            logger.info(f"DEMO: promote_prompt_variant {version_id} winner={winner}")
        else:
            raise


async def update_channel_policy(data: dict):
    """Bayesian update of channel policy bandit for a (segment × tier × channel) cell."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO channel_policy (
                    segment, life_event_type, risk_tier, content_strategy,
                    primary_signal_type, channel, bandit_alpha, bandit_beta
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (segment, risk_tier, channel, content_strategy, primary_signal_type)
                DO UPDATE SET
                    bandit_alpha = channel_policy.bandit_alpha + $7,
                    bandit_beta  = channel_policy.bandit_beta  + $8,
                    updated_at = NOW()
            """,
                data["segment"], data.get("life_event_type"), data["risk_tier"],
                data.get("content_strategy"), data.get("primary_signal_type"),
                data["channel"],
                float(data["alpha_increment"]), float(data["beta_increment"]),
            )
    except Exception:
        if DEMO_MODE:
            logger.info(
                f"DEMO: update_channel_policy "
                f"segment={data['segment']} tier={data['risk_tier']} "
                f"channel={data['channel']} alpha+={data['alpha_increment']}"
            )
        else:
            raise


async def write_insight_cards(cards: list[dict], generated_date: str):
    """Writes nightly insight cards to the DB."""
    try:
        pool = await get_pool()
        if pool is None:
            raise RuntimeError("no pool")
        async with pool.acquire() as conn:
            for card in cards:
                await conn.execute("""
                    INSERT INTO insight_cards (
                        generated_date, severity, title, what, why,
                        where_affected, recommend, metric_name, metric_delta,
                        affected_customers
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                    generated_date,
                    card.get("severity"), card.get("title"),
                    card.get("what"), card.get("why"), card.get("where"),
                    card.get("recommend"), card.get("metric_name"),
                    card.get("metric_delta"), card.get("affected_customers"),
                )
    except Exception:
        if DEMO_MODE:
            logger.info(f"DEMO: write_insight_cards n={len(cards)} date={generated_date}")
        else:
            raise
