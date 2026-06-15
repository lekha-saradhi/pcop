import json
import logging
from datetime import datetime, timezone
from ..state import HeraldState
from ..db.writes import (
    write_content_store,
    update_outreach_log_status,
    write_human_review_queue,
)
from ..kafka.producer import get_kafka_producer

logger = logging.getLogger(__name__)


async def chronicle_node(state: HeraldState) -> dict:
    customer_id = state["customer_id"]
    brief = state["brief"]
    event = state["action_plan_event"]
    outreach_id = event.get("outreach_id")

    content_store_id = await write_content_store({
        "outreach_id": outreach_id,
        "channel": state["channel"],
        "subject_line": (
            state["generated_content"].get("subject_line")
            if state["channel"] == "email" else None
        ),
        "body_content": json.dumps(state["generated_content"]),
        "ab_variant_content": (
            json.dumps(state.get("ab_variant")) if state.get("ab_variant") else None
        ),
        "cta_text": (
            state["generated_content"].get("cta_text")
            or state["generated_content"].get("cta_label")
        ),
        "compliance_status": state.get("compliance_status", "unknown"),
        "compliance_notes": state.get("compliance_notes"),
        "prompt_version": brief.get("prompt_version_id"),
        "llm_model": "kimi-k2-5",
        "content_strategy": brief.get("content_strategy"),
        "tone_modifiers": brief.get("tone_modifiers", []),
        "reason_codes_used": brief.get("reason_codes", []),
    })

    new_status = "sent" if state.get("dispatched") else (
        "human_review" if state.get("human_review_required") else "failed"
    )
    await update_outreach_log_status(outreach_id, new_status)

    if state.get("human_review_required"):
        await write_human_review_queue({
            "outreach_id": outreach_id,
            "customer_id": customer_id,
            "channel": state["channel"],
            "content_store_id": content_store_id,
            "compliance_notes": state.get("compliance_notes"),
            "priority": event.get("action_plan", {}).get("priority", 3),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning(
            f"CHRONICLE: Human review queued for {customer_id} outreach_id={outreach_id}"
        )

    if state.get("dispatched"):
        kafka_payload = {
            "customer_id": customer_id,
            "outreach_id": outreach_id,
            "content_store_id": content_store_id,
            "channel": state["channel"],
            "offer_code": brief.get("offer_code"),
            "prompt_version_id": brief.get("prompt_version_id"),
            "ab_variant": "B" if state.get("ab_variant") and _is_variant_b(customer_id) else "A",
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "risk_tier": event.get("risk_tier"),
            "final_score": event.get("final_score"),
            "life_events": [e["event_type"] for e in event.get("final_events", [])],
            "content_strategy": brief.get("content_strategy"),
        }

        producer = get_kafka_producer()
        producer.produce(
            topic="pcop.dispatched.v1",
            key=customer_id,
            value=json.dumps(kafka_payload, default=str).encode("utf-8"),
        )
        producer.flush()

        logger.info(
            f"CHRONICLE: Published pcop.dispatched.v1 for {customer_id} "
            f"content_store_id={content_store_id}"
        )

    return {"content_store_id": content_store_id}


def _is_variant_b(customer_id: str) -> bool:
    return int(customer_id.replace("C-", "")) % 2 == 1
