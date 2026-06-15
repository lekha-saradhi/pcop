import logging
from ..state import HeraldState
from ..dispatchers.email import send_email
from ..dispatchers.sms import send_sms
from ..dispatchers.push import send_push
from ..dispatchers.rm_queue import send_to_rm_queue

logger = logging.getLogger(__name__)

DISPATCHERS = {
    "email": send_email,
    "sms": send_sms,
    "app": send_push,
    "call": send_to_rm_queue,
    "rm_visit": send_to_rm_queue,
}


async def dispatch_node(state: HeraldState) -> dict:
    if state.get("human_review_required"):
        logger.info(f"DISPATCH: Skipping {state['customer_id']} — pending human review")
        return {"dispatched": False}

    customer_id = state["customer_id"]
    channel = state["channel"]
    content = state["generated_content"]
    brief = state["brief"]
    event = state["action_plan_event"]

    logger.info(f"DISPATCH: Sending {channel} to {customer_id}")

    dispatcher = DISPATCHERS.get(channel)
    if not dispatcher:
        logger.error(f"DISPATCH: No dispatcher for channel={channel}")
        return {"dispatched": False}

    customer_email = None
    customer_phone = None
    customer_push_token = None

    if channel == "email":
        from ..db.reads import get_customer_contact
        contact = await get_customer_contact(customer_id)
        customer_email = contact.get("email", "")
    elif channel == "sms":
        from ..db.reads import get_customer_contact
        contact = await get_customer_contact(customer_id)
        customer_phone = contact.get("phone_mobile", "")
    elif channel == "app":
        from ..db.reads import get_push_token
        customer_push_token = await get_push_token(customer_id)

    dispatch_payload = {
        "customer_id": customer_id,
        "outreach_id": event.get("outreach_id"),
        "content": content,
        "ab_variant": state.get("ab_variant"),
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "customer_push_token": customer_push_token,
        "rm_id": event.get("action_plan", {}).get("owner_id"),
        "priority": event.get("action_plan", {}).get("priority", 3),
        "offer_code": brief.get("offer_code"),
    }

    try:
        dispatch_result = await dispatcher(dispatch_payload)
        logger.info(
            f"DISPATCH: Sent {channel} for {customer_id} — "
            f"provider_id={dispatch_result.get('provider_message_id')}"
        )
        return {
            "dispatched": True,
            "dispatch_provider_id": dispatch_result.get("provider_message_id"),
        }
    except Exception as e:
        logger.error(f"DISPATCH: Failed for {customer_id}: {e}", exc_info=True)
        return {"dispatched": False}
