import os
import json
import logging
from confluent_kafka import Consumer, KafkaError
from ..db.writes import write_interaction_event
from ..db.reads import get_outreach_context

logger = logging.getLogger(__name__)

DEMO_MODE = os.environ.get("VERDICT_DEMO_MODE", "true").lower() == "true"


class CollectConsumer:
    """
    Listens to pcop.interactions.v1.
    Enriches each event with attribution context from HERALD's
    content_store and outreach_log records.
    Writes to interaction_events table.
    """

    def __init__(self):
        self.consumer = Consumer({
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": "verdict-collect",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self.consumer.subscribe(["pcop.interactions.v1"])
        self._running = False

    async def _process(self, raw_event: dict):
        outreach_id = raw_event["outreach_id"]

        context = await get_outreach_context(outreach_id)

        enriched_event = {
            **raw_event,
            "content_store_id": context.get("content_store_id"),
            "prompt_version_id": context.get("prompt_version"),
            "content_strategy": context.get("content_strategy"),
            "ab_variant": context.get("ab_variant"),
            "life_events_at_send": context.get("life_events"),
            "risk_tier_at_send": context.get("risk_tier"),
            "final_score_at_send": context.get("final_score"),
            "treatability_score_at_send": context.get("treatability_score"),
        }

        await write_interaction_event(enriched_event)
        logger.info(
            f"COLLECT: {raw_event['event_type']} for "
            f"customer={raw_event['customer_id']} "
            f"channel={raw_event['channel']}"
        )

    def run(self):
        import asyncio
        self._running = True
        logger.info("COLLECT: Starting consumer loop on pcop.interactions.v1")
        loop = asyncio.get_event_loop()
        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"COLLECT: Kafka error: {msg.error()}")
                    continue
                try:
                    raw_event = json.loads(msg.value().decode("utf-8"))
                    loop.run_until_complete(self._process(raw_event))
                    self.consumer.commit(message=msg)
                except Exception as e:
                    logger.error(f"COLLECT: Failed to process event: {e}")
        finally:
            self.consumer.close()
            logger.info("COLLECT: Consumer stopped")

    def stop(self):
        self._running = False
