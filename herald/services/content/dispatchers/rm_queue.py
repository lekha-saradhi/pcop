import os
import logging

logger = logging.getLogger(__name__)


async def send_to_rm_queue(payload: dict) -> dict:
    demo_mode = os.environ.get("HERALD_DEMO_MODE", "true").lower() == "true"
    content = payload["content"]
    rm_id = payload.get("rm_id", "unassigned")
    channel = "call" if "opening" in content else "rm_visit"

    task = {
        "customer_id": payload["customer_id"],
        "outreach_id": payload.get("outreach_id"),
        "rm_id": rm_id,
        "priority": payload.get("priority", 3),
        "offer_code": payload.get("offer_code"),
        "channel": channel,
        "content": content,
    }

    if demo_mode:
        logger.info(
            f"[DEMO RM QUEUE] RM: {rm_id} | Customer: {payload['customer_id']} | "
            f"Channel: {channel} | Priority: {payload.get('priority', 3)}"
        )
        return {"provider_message_id": f"demo-rm-{payload.get('outreach_id')}"}

    import aiohttp

    rm_queue_url = os.environ.get("RM_TASK_QUEUE_URL", "")
    rm_api_key = os.environ.get("RM_API_KEY", "")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{rm_queue_url}/tasks",
            json=task,
            headers={"Authorization": f"Bearer {rm_api_key}"},
        ) as resp:
            result = await resp.json()
            return {"provider_message_id": result.get("task_id", "")}
