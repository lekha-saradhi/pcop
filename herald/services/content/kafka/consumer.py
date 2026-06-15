import asyncio
import json
import logging
import os
from confluent_kafka import Consumer, KafkaError
from ..graph.builder import build_herald_graph

logger = logging.getLogger(__name__)


class HeraldConsumer:
    """
    Kafka consumer for pcop.action_plans.v1.
    Each message is one customer's action plan from COMPASS.
    Triggers one HERALD graph execution per message.

    Demo mode: direct invocation, no Kafka needed.
    Production: parallel workers, one per Kafka partition.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.graph = build_herald_graph()

        if not demo_mode:
            self.consumer = Consumer({
                "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
                "group.id": "herald-layer5",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "max.poll.interval.ms": 120000,
            })
            self.consumer.subscribe(["pcop.action_plans.v1"])

    async def run(self):
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                action_plan_event = json.loads(msg.value().decode("utf-8"))
                await self._process(action_plan_event)
                self.consumer.commit(message=msg)

        except KeyboardInterrupt:
            logger.info("HeraldConsumer shutting down")
        finally:
            self.consumer.close()

    async def _process(self, action_plan_event: dict):
        customer_id = action_plan_event.get("customer_id")

        if not action_plan_event.get("action_plan", {}).get("channel"):
            logger.info(f"HERALD: Skipping {customer_id} — monitor plan, no channel")
            return

        logger.info(
            f"HERALD: Processing {customer_id} — "
            f"channel={action_plan_event['action_plan']['channel']}"
        )

        initial_state = {
            "action_plan_event": action_plan_event,
            "customer_id": customer_id,
            "channel": action_plan_event["action_plan"]["channel"],
            "brief": None,
            "generated_content": None,
            "ab_variant": None,
            "compliance_status": None,
            "compliance_notes": None,
            "retry_count": 0,
            "dispatched": False,
            "dispatch_provider_id": None,
            "content_store_id": None,
            "human_review_required": False,
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            logger.info(
                f"HERALD: Completed {customer_id} — "
                f"compliance={result.get('compliance_status')} "
                f"dispatched={result.get('dispatched')}"
            )
        except Exception as e:
            logger.error(f"HERALD: Failed for {customer_id}: {e}", exc_info=True)
