import logging
from ..db.reads import get_distinct_channel_policy_cells, get_channel_uplift_by_cell
from ..db.writes import update_channel_policy

logger = logging.getLogger(__name__)


async def update_channel_policy_from_uplift():
    """
    Bayesian update of channel preference rankings.

    For each (segment × life_event_type × risk_tier × content_strategy) cell:
      Update Beta(alpha, beta) for each channel based on new DR uplift data.
      The channel preference rank table is read by COMPASS NBA agent
      as a soft prior — COMPASS can override based on specific customer context.

    New HERALD-specific dimension: content_strategy
      We rank channels separately for full_retention vs graceful_retention.
      For graceful_retention: rm_visit typically outperforms email
        (a bereavement-sensitive customer needs human contact)
      For full_retention: email + in-app typically outperforms call
        (digital-native customers respond better to digital channels)

    New ARGUS-specific dimension: primary_signal_type
      For cfsi_stress primary signal: call typically outperforms all
      For lifecycle_mcc_marriage: email with product info outperforms
      For nexus_correlation (joint alarm, severe): rm_visit outperforms
    """
    cells = await get_distinct_channel_policy_cells()

    total_updates = 0
    for cell in cells:
        channel_uplifts = await get_channel_uplift_by_cell(**cell)

        for channel_data in channel_uplifts:
            channel = channel_data["channel"]
            dr_uplift = channel_data.get("dr_uplift", 0) or 0
            n = channel_data.get("n_samples", 0) or 0

            if n < 10:
                continue

            # Convert uplift to success/failure counts for Beta update
            successes = max(0, int(n * max(0, dr_uplift)))
            failures = n - successes

            await update_channel_policy({
                "segment": cell["segment"],
                "life_event_type": cell.get("life_event_type"),
                "risk_tier": cell["risk_tier"],
                "content_strategy": cell.get("content_strategy"),
                "primary_signal_type": cell.get("primary_signal_type"),
                "channel": channel,
                "alpha_increment": successes,
                "beta_increment": failures,
            })

            total_updates += 1
            logger.info(
                f"ROUTE: Updated channel policy — "
                f"segment={cell['segment']} tier={cell['risk_tier']} "
                f"channel={channel} dr_uplift={dr_uplift:.4f} n={n}"
            )

    logger.info(f"ROUTE: Policy update complete — {total_updates} channel cells updated")
