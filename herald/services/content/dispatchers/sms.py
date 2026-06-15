import os
import logging

logger = logging.getLogger(__name__)

STOP_INSTRUCTION = " Reply STOP to opt out"


async def send_sms(payload: dict) -> dict:
    demo_mode = os.environ.get("HERALD_DEMO_MODE", "true").lower() == "true"
    content = payload["content"]

    message_body = content.get("message", "")
    full_message = message_body + STOP_INSTRUCTION

    if len(full_message) > 160:
        max_body_len = 160 - len(STOP_INSTRUCTION)
        message_body = message_body[:max_body_len - 3] + "..."
        full_message = message_body + STOP_INSTRUCTION

    if demo_mode:
        logger.info(
            f"[DEMO SMS] To: {payload.get('customer_phone')}\n"
            f"Message ({len(full_message)} chars): {full_message}"
        )
        return {"provider_message_id": f"demo-sms-{payload.get('outreach_id')}"}

    from twilio.rest import Client

    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )
    message = client.messages.create(
        body=full_message,
        from_=os.environ["TWILIO_FROM_NUMBER"],
        to=payload["customer_phone"],
    )
    return {"provider_message_id": message.sid}
