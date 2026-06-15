import logging
from datetime import datetime, timezone
from langchain_core.tools import tool
from ..db.connection import get_db_session

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = {
    "job_change", "relocation", "salary_change", "financial_stress",
    "marriage", "bereavement", "retirement", "home_purchase",
    "new_baby", "churn_intent",
}


def _score_to_tier(score: float) -> str:
    if score >= 0.85:
        return "critical"
    elif score >= 0.65:
        return "high"
    elif score >= 0.40:
        return "medium"
    elif score >= 0.20:
        return "watch"
    return "low"


@tool
async def write_life_event_tool(
    customer_id: str,
    event_type: str,
    confidence: float,
    evidence: list[str],
    source: str,
    risk_adjustment: float,
) -> dict:
    """
    Writes a confirmed life event to the life_events table.
    Called by COGNITION after confirming an event with confidence >= 0.60.
    Called by VERIFY for high-confidence signals.

    Args:
        customer_id: Customer identifier
        event_type: One of the defined life event types
        confidence: 0.0 to 1.0
        evidence: List of evidence strings
        source: 'llm_cognition' or 'rule_verify'
        risk_adjustment: Float between -0.30 and +0.30
    """
    if event_type not in VALID_EVENT_TYPES:
        return {"success": False, "error": f"Invalid event_type: {event_type}"}

    if not 0.0 <= confidence <= 1.0:
        return {"success": False, "error": f"Confidence out of range: {confidence}"}

    risk_adjustment = max(-0.30, min(0.30, risk_adjustment))

    async with get_db_session() as session:
        row = await session.fetchrow("""
            INSERT INTO life_events
              (customer_id, event_type, confidence, evidence, source,
               risk_adjustment, detected_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING event_id
        """, customer_id, event_type, confidence, evidence, source, risk_adjustment)

        event_id = row["event_id"]
        logger.info(
            f"write_life_event: customer={customer_id} "
            f"event={event_type} confidence={confidence:.2f} event_id={event_id}"
        )

        return {
            "success": True,
            "event_id": event_id,
            "event": {
                "event_type": event_type,
                "confidence": confidence,
                "evidence": evidence,
                "source": source,
                "risk_adjustment": risk_adjustment,
            },
        }


@tool
async def adjust_risk_score_tool(
    customer_id: str,
    adjustment: float,
    reason: str,
) -> dict:
    """
    Applies a risk adjustment to the customer's churn score.
    COGNITION calls this once after confirming all events.

    The adjustment is additive but the final score is clamped to [0.0, 1.0].
    The adjusted score is written back to churn_scores as a new row
    with scoring_pass='compass-adjusted'.

    Args:
        customer_id: Customer identifier
        adjustment: Float between -0.30 and +0.30
        reason: Brief explanation for the adjustment
    """
    adjustment = max(-0.30, min(0.30, adjustment))

    async with get_db_session() as session:
        current = await session.fetchrow("""
            SELECT final_score, risk_tier
            FROM churn_scores
            WHERE customer_id = $1
            ORDER BY scored_at DESC
            LIMIT 1
        """, customer_id)

        if current is None:
            return {"success": False, "error": "No churn score found"}

        old_score = float(current.get("final_score") or 0.0)
        new_score = max(0.0, min(1.0, old_score + adjustment))
        new_tier = _score_to_tier(new_score)

        await session.execute("""
            INSERT INTO churn_scores
              (customer_id, score_date, final_score, risk_tier,
               scoring_pass, scored_at, model_version)
            VALUES ($1, CURRENT_DATE, $2, $3, 'compass-adjusted', NOW(), 'compass-v1')
        """, customer_id, new_score, new_tier)

        logger.info(
            f"adjust_risk_score: customer={customer_id} "
            f"{old_score:.3f} → {new_score:.3f} ({adjustment:+.3f}) "
            f"tier: {current['risk_tier']} → {new_tier} reason: {reason}"
        )

        return {
            "success": True,
            "old_score": old_score,
            "new_score": new_score,
            "old_tier": current["risk_tier"],
            "new_tier": new_tier,
        }


@tool
async def write_action_plan_tool(
    customer_id: str,
    channel: str,
    offer_code: str,
    timing: str,
    owner_id: str,
    priority: int,
    rationale: str,
) -> dict:
    """
    Records the NBA decision from COMPASS.
    Written to action_plans table. DISPATCH reads this to publish to Kafka.

    Args:
        customer_id: Customer identifier
        channel: Selected outreach channel
        offer_code: Selected offer code
        timing: ISO datetime for outreach
        owner_id: RM id or 'system'
        priority: 1 (highest) to 5
        rationale: Brief reason string
    """
    valid_channels = {"email", "sms", "app", "call", "rm_visit"}
    if channel not in valid_channels:
        return {"success": False, "error": f"Invalid channel: {channel}"}

    async with get_db_session() as session:
        row = await session.fetchrow("""
            INSERT INTO action_plans
              (customer_id, channel, offer_code, timing, owner_id,
               priority, rationale, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            RETURNING plan_id
        """, customer_id, channel, offer_code, timing, owner_id, priority, rationale)

        return {
            "success": True,
            "plan_id": row["plan_id"],
            "action_plan": {
                "channel": channel,
                "offer_code": offer_code,
                "timing": timing,
                "owner_id": owner_id,
                "priority": priority,
                "rationale": rationale,
                "suppressed": False,
            },
        }


@tool
async def write_outreach_log_tool(
    customer_id: str,
    channel: str | None,
    risk_tier: str | None,
    life_events: list[str],
    offer_code: str | None,
    status: str,
    dispatched_at: str,
    holdout_group: bool,
) -> dict:
    """
    Writes an outreach log record for audit trail.
    Always called by DISPATCH, even for suppressed and monitor plans.

    Args:
        customer_id: Customer identifier
        channel: Outreach channel (None for monitor plans)
        risk_tier: Current risk tier
        life_events: List of life event type strings
        offer_code: Offer code (None for monitor plans)
        status: 'queued' | 'suppressed' | 'monitor'
        dispatched_at: ISO datetime
        holdout_group: Whether this customer is in the holdout group
    """
    async with get_db_session() as session:
        row = await session.fetchrow("""
            INSERT INTO outreach_log
              (customer_id, channel, risk_tier, life_events,
               offer_code, status, dispatched_at, holdout_group)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING outreach_id
        """, customer_id, channel, risk_tier, life_events,
             offer_code, status, dispatched_at, holdout_group)

        return {"success": True, "outreach_id": row["outreach_id"]}
