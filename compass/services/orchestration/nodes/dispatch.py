import json
import logging
from datetime import datetime, timezone
from ..state import CompassState
from ..tools.db_writes import write_outreach_log_tool
from ..kafka.producer import get_kafka_producer

logger = logging.getLogger(__name__)


async def dispatch_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    action_plan = state.get("action_plan", {})
    dispatch_ts = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"DISPATCH: Writing outputs for {customer_id} — "
        f"channel={action_plan.get('channel')} "
        f"suppressed={action_plan.get('suppressed')}"
    )

    outreach_result = await write_outreach_log_tool.ainvoke({
        "customer_id": customer_id,
        "channel": action_plan.get("channel"),
        "risk_tier": state.get("risk_tier"),
        "life_events": [e["event_type"] for e in state.get("final_events", [])],
        "offer_code": action_plan.get("offer_code"),
        "status": "suppressed" if action_plan.get("suppressed") else "queued",
        "dispatched_at": dispatch_ts,
        "holdout_group": False,
    })

    outreach_id = outreach_result.get("outreach_id")

    if not action_plan.get("suppressed") and action_plan.get("channel"):
        kafka_payload = {
            "customer_id": customer_id,
            "outreach_id": outreach_id,
            "as_of_date": state["as_of_date"],
            "risk_tier": state.get("risk_tier"),
            "final_score": state.get("final_score"),
            "action_score": state.get("action_score"),
            "final_events": state.get("final_events", []),
            "action_plan": action_plan,
            "dispatch_timestamp": dispatch_ts,
        }

        producer = get_kafka_producer()
        producer.produce(
            topic="pcop.action_plans.v1",
            key=customer_id,
            value=json.dumps(kafka_payload, default=str).encode("utf-8"),
        )
        producer.flush()

        logger.info(
            f"DISPATCH: Published to Kafka for {customer_id} "
            f"outreach_id={outreach_id}"
        )
    else:
        logger.info(
            f"DISPATCH: No Kafka publish for {customer_id} "
            f"(suppressed={action_plan.get('suppressed')})"
        )

    return {
        "dispatch_timestamp": dispatch_ts,
        "outreach_id": outreach_id,
    }
