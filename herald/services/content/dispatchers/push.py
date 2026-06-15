import os
import json
import logging

logger = logging.getLogger(__name__)

FCM_URL = "https://fcm.googleapis.com/fcm/send"


async def send_push(payload: dict) -> dict:
    demo_mode = os.environ.get("HERALD_DEMO_MODE", "true").lower() == "true"
    content = payload["content"]
    push_token = payload.get("customer_push_token", "")

    fcm_payload = {
        "to": push_token,
        "notification": {
            "title": content.get("title", ""),
            "body": content.get("card_body", ""),
        },
        "data": {
            "cta_label": content.get("cta_label", ""),
            "offer_code": payload.get("offer_code", ""),
            "outreach_id": str(payload.get("outreach_id", "")),
        },
    }

    if demo_mode:
        logger.info(
            f"[DEMO PUSH] Token: {push_token}\n"
            f"Title: {content.get('title')}\n"
            f"Body: {content.get('card_body')}\n"
            f"CTA: {content.get('cta_label')}"
        )
        return {"provider_message_id": f"demo-push-{payload.get('outreach_id')}"}

    import aiohttp

    server_key = os.environ["FCM_SERVER_KEY"]
    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(FCM_URL, headers=headers, json=fcm_payload) as resp:
            result = await resp.json()
            message_id = result.get("results", [{}])[0].get("message_id", "")
            return {"provider_message_id": message_id}
