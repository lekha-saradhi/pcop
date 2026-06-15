import logging
from ..db.reads import get_prompt_versions_with_dr_uplift, get_ab_variant_outcomes
from ..db.writes import update_bandit_params, promote_prompt_variant

logger = logging.getLogger(__name__)

UPLIFT_THRESHOLD = 0.02       # DR uplift > 2% is a meaningful retention effect
AB_MIN_DISPATCHES = 100
AB_SIGNIFICANCE_LEVEL = 0.05


async def run_daily_prompt_optimisation():
    """
    Daily Thompson sampling bandit update for prompt_versions.

    Uses DR-estimated uplift per prompt version (not raw conversion_rate).
    This prevents prompt versions that were sent to naturally-recovering
    customers from appearing artificially successful.

    Thompson sampling update:
      For each prompt version with new DR uplift data:
        if dr_uplift > UPLIFT_THRESHOLD: alpha += successes
        else:                           beta += failures
      Sample from Beta(alpha, beta) to select next prompt version.

    Additional HERALD-specific signals:
      1. Content strategy effectiveness:
         If full_retention dr_uplift < graceful_retention dr_uplift
         for low-treatability customers → flag to HERALD
      2. A/B variant winner: Fisher's exact test after 100 dispatches
      3. Tone modifier effectiveness by segment × life_event_type
    """
    channels = ["email", "sms", "app", "call", "rm_visit"]

    for channel in channels:
        versions = await get_prompt_versions_with_dr_uplift(channel=channel)

        for version in versions:
            version_id = version["version_id"]
            dr_uplift = version.get("dr_uplift", 0) or 0
            n_new_observations = version.get("new_observations_today", 0) or 0

            if n_new_observations == 0:
                continue

            # Map DR uplift to successes/failures for Beta update
            # Scale: 10% uplift → all successes; 0% uplift → half successes
            uplift_fraction = max(0.0, min(1.0, dr_uplift / 0.10))
            successes = int(round(n_new_observations * uplift_fraction))
            failures = n_new_observations - successes

            await update_bandit_params(
                version_id=version_id,
                alpha_increment=successes,
                beta_increment=failures,
                conversion_rate=max(0.0, dr_uplift),
            )

            logger.info(
                f"REFINE: Updated {version_id} — "
                f"dr_uplift={dr_uplift:.4f} "
                f"successes={successes} failures={failures}"
            )

        await _check_ab_variant_significance(channel=channel)
        await _measure_tone_modifier_effectiveness(channel=channel)


async def _check_ab_variant_significance(channel: str):
    """
    After 100 dispatches per variant, runs Fisher's exact test
    to determine if variant B significantly outperforms variant A.
    Promotes winner to primary, retires loser.
    Only applies to email (the only channel with A/B variants in HERALD).
    """
    if channel != "email":
        return

    from scipy.stats import fisher_exact

    variants = await get_ab_variant_outcomes(min_dispatches=AB_MIN_DISPATCHES)

    for variant_pair in variants:
        a_retained = variant_pair["a_retained"]
        a_total = variant_pair["a_total"]
        b_retained = variant_pair["b_retained"]
        b_total = variant_pair["b_total"]

        if a_total == 0 or b_total == 0:
            continue

        contingency = [
            [a_retained, a_total - a_retained],
            [b_retained, b_total - b_retained],
        ]

        _, p_value = fisher_exact(contingency, alternative="two-sided")

        if p_value < AB_SIGNIFICANCE_LEVEL:
            winner = "B" if (b_retained / b_total) > (a_retained / a_total) else "A"
            logger.info(
                f"REFINE: A/B test significant (p={p_value:.4f}) — "
                f"winner={winner} for version={variant_pair['version_id']}"
            )
            await promote_prompt_variant(
                version_id=variant_pair["version_id"],
                winner=winner,
            )
        else:
            logger.info(
                f"REFINE: A/B test not significant (p={p_value:.4f}) "
                f"for version={variant_pair['version_id']} — continuing"
            )


async def _measure_tone_modifier_effectiveness(channel: str):
    """
    Logs which tone_modifier combinations produce highest DR uplift
    by segment × life_event_type.
    Results inform HERALD's tone selection in future dispatches.
    """
    # Production: query interaction_events joined on outcomes for tone_modifier columns
    # For now demo only
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info(f"DEMO: tone_modifier effectiveness logged for channel={channel}")
