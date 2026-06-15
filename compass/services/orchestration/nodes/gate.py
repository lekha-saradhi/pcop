import logging
from datetime import datetime, timezone
from ..state import CompassState
from ..tools.db_reads import get_channel_history_raw, get_consent_flags_raw

logger = logging.getLogger(__name__)

COOLDOWN_HOURS = {
    "email": 72,
    "sms": 48,
    "app": 24,
    "call": 168,
    "rm_visit": 336,
}

FATIGUE_LIMIT_30D = 4
RESCUE_THRESHOLD = 0.92


async def gate_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    action_plan = state.get("action_plan", {})
    channel = action_plan.get("channel") if action_plan else None

    if channel is None:
        return {
            "gate_decision": "approved",
            "gate_reason": None,
            "action_plan": {**action_plan, "suppressed": False},
        }

    final_score = state.get("final_score") or 0.0

    if final_score > RESCUE_THRESHOLD:
        logger.info(
            f"GATE: Rescue override for {customer_id} "
            f"(score={final_score:.3f} > {RESCUE_THRESHOLD})"
        )
        return {
            "gate_decision": "approved",
            "gate_reason": "rescue_override",
            "action_plan": {**action_plan, "suppressed": False},
        }

    consent_flags = await get_consent_flags_raw(customer_id)
    channel_history = await get_channel_history_raw(customer_id, days=30)

    consent_key = f"{channel}_opt_in"
    if not consent_flags.get(consent_key, True):
        reason = f"customer_opted_out_{channel}"
        logger.info(f"GATE: Suppressed {customer_id} — {reason}")
        return {
            "gate_decision": "suppressed",
            "gate_reason": reason,
            "action_plan": {**action_plan, "suppressed": True},
        }

    cooldown_hours = COOLDOWN_HOURS.get(channel, 24)
    last_contact = _get_last_contact_for_channel(channel_history, channel)

    if last_contact is not None:
        hours_since = (
            datetime.now(timezone.utc) - last_contact
        ).total_seconds() / 3600
        if hours_since < cooldown_hours:
            reason = f"cooldown_{channel}_{int(hours_since)}h_of_{cooldown_hours}h"
            logger.info(f"GATE: Suppressed {customer_id} — {reason}")
            return {
                "gate_decision": "suppressed",
                "gate_reason": reason,
                "action_plan": {**action_plan, "suppressed": True},
            }

    touches_30d = len(channel_history)
    if touches_30d >= FATIGUE_LIMIT_30D:
        reason = f"fatigue_limit_{touches_30d}_touches_in_30d"
        logger.info(f"GATE: Suppressed {customer_id} — {reason}")
        return {
            "gate_decision": "suppressed",
            "gate_reason": reason,
            "action_plan": {**action_plan, "suppressed": True},
        }

    logger.info(
        f"GATE: Approved {customer_id} — channel={channel}, touches_30d={touches_30d}"
    )
    return {
        "gate_decision": "approved",
        "gate_reason": None,
        "action_plan": {**action_plan, "suppressed": False},
    }


def _get_last_contact_for_channel(
    history: list, channel: str
) -> datetime | None:
    channel_contacts = [h for h in history if h.get("channel") == channel]
    if not channel_contacts:
        return None
    timestamps = [
        datetime.fromisoformat(h["dispatched_at"])
        for h in channel_contacts
        if h.get("dispatched_at")
    ]
    return max(timestamps) if timestamps else None
