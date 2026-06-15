import json
import logging
import hashlib
from datetime import datetime, timezone
from ..db.reads import get_active_holdouts, get_current_churn_score
from ..db.writes import write_holdout_registry, rescue_holdout_customer

logger = logging.getLogger(__name__)

HOLDOUT_FRACTION = 0.15
RESCUE_THRESHOLD = 0.92       # Must match COMPASS GATE rescue threshold
MAX_HOLDOUT_DAYS = 30


async def assign_holdout(
    campaign_id: str,
    customer_ids: list[str],
    risk_tier: str,
    segment: str,
    region: str,
) -> dict[str, bool]:
    """
    Assigns customers to treatment or holdout group.

    Stratification: within each (risk_tier × segment × region) cell,
    exactly 15% are assigned to holdout. This ensures the holdout group
    is comparable to the treatment group on all known confounders.

    Assignment is deterministic by customer_id hash — the same customer
    always gets the same assignment for the same campaign. This prevents
    the same customer from always being in control across campaigns.

    Returns: dict mapping customer_id → is_holdout (True = holdout)
    """
    assignments = {}

    for customer_id in customer_ids:
        hash_input = f"{customer_id}:{campaign_id}:{risk_tier}:{segment}:{region}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        is_holdout = (hash_val % 100) < int(HOLDOUT_FRACTION * 100)
        assignments[customer_id] = is_holdout

        if is_holdout:
            await write_holdout_registry({
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "risk_tier_at_entry": risk_tier,
                "risk_score_at_entry": None,
                "entered_holdout_at": datetime.now(timezone.utc).isoformat(),
            })

    holdout_count = sum(assignments.values())
    logger.info(
        f"HOLDOUT: Assigned {holdout_count}/{len(customer_ids)} "
        f"to holdout for campaign={campaign_id} "
        f"tier={risk_tier} segment={segment}"
    )

    return assignments


async def run_rescue_check():
    """
    Hourly job: checks all active holdout customers for rescue threshold breach.

    A holdout customer whose CHRONOS churn score exceeds 0.92 is immediately
    rescued — moved to treatment group and passed to COMPASS for action plan
    generation. This matches COMPASS GATE's rescue override threshold exactly.

    Published to pcop.alarms.v1 so COMPASS picks it up immediately.
    """
    from ..kafka.producer import get_kafka_producer

    active_holdouts = await get_active_holdouts()

    if not active_holdouts:
        return

    rescued_count = 0
    for holdout in active_holdouts:
        customer_id = holdout["customer_id"]

        current_score = await get_current_churn_score(customer_id)
        final_score = current_score.get("final_score", 0)

        entered_at = holdout["entered_holdout_at"]
        if isinstance(entered_at, str):
            entered_at = datetime.fromisoformat(entered_at)
        if entered_at.tzinfo is None:
            entered_at = entered_at.replace(tzinfo=timezone.utc)

        days_in_holdout = (datetime.now(timezone.utc) - entered_at).days

        should_rescue = (
            final_score > RESCUE_THRESHOLD
            or days_in_holdout >= MAX_HOLDOUT_DAYS
        )

        if should_rescue:
            exit_reason = "rescue_threshold" if final_score > RESCUE_THRESHOLD else "timeout_30d"

            await rescue_holdout_customer(
                customer_id=customer_id,
                exit_reason=exit_reason,
            )

            if final_score > RESCUE_THRESHOLD:
                try:
                    producer = get_kafka_producer()
                    producer.produce(
                        topic="pcop.alarms.v1",
                        key=customer_id,
                        value=json.dumps({
                            "customer_id": customer_id,
                            "alarm_severity": "CRITICAL",
                            "alarm_timestamp": datetime.now(timezone.utc).isoformat(),
                            "signal_details": [],
                            "rescue_from_holdout": True,
                        }).encode("utf-8"),
                    )
                    producer.flush()
                except Exception as e:
                    logger.warning(f"HOLDOUT: Failed to publish rescue alarm for {customer_id}: {e}")

            rescued_count += 1
            logger.info(
                f"HOLDOUT: Rescued {customer_id} — "
                f"score={final_score:.3f} days={days_in_holdout} "
                f"reason={exit_reason}"
            )

    if rescued_count:
        logger.info(f"HOLDOUT: Rescued {rescued_count} customers in this check")
