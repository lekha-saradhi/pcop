import asyncio
import json
import logging
import os
from confluent_kafka import Consumer, KafkaError
from ..graph.builder import build_demo_graph, build_compass_graph
from ..state import CompassState

logger = logging.getLogger(__name__)


class CompassConsumer:
    """
    Kafka consumer that processes ARGUS alarm events.
    Each alarm triggers one COMPASS graph execution per customer.

    Demo mode: processes events sequentially (no parallelism needed for 20 customers)
    Production mode: runs N workers in parallel (target ~23 customers/second)
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.graph = build_demo_graph() if demo_mode else build_compass_graph()

        self.consumer = Consumer({
            "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            "group.id": "compass-layer4",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 30000,
        })
        self.consumer.subscribe(["pcop.alarms.v1"])
        logger.info(
            f"CompassConsumer initialised. demo_mode={demo_mode}, topic=pcop.alarms.v1"
        )

    async def run(self):
        logger.info("CompassConsumer: Starting consumer loop")
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    await asyncio.sleep(0)
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Kafka error: {msg.error()}")
                    continue

                await self._process_message(msg)
                self.consumer.commit(message=msg)

        except asyncio.CancelledError:
            logger.info("CompassConsumer: Cancelled")
        except KeyboardInterrupt:
            logger.info("CompassConsumer: Shutting down")
        finally:
            self.consumer.close()

    async def _process_message(self, msg):
        alarm: dict = {}
        try:
            alarm = json.loads(msg.value().decode("utf-8"))
            customer_id = alarm["customer_id"]

            logger.info(
                f"CompassConsumer: Processing alarm for {customer_id} "
                f"(severity={alarm.get('alarm_severity')})"
            )

            initial_state: CompassState = {
                "customer_id": customer_id,
                "as_of_date": alarm.get("alarm_timestamp", "")[:10],
                "alarm_severity": alarm.get("alarm_severity", "LOW"),
                "alarm_timestamp": alarm.get("alarm_timestamp", ""),
                "signal_results": alarm.get("signal_details", []),
                "risk_tier": None,
                "final_score": None,
                "action_score": None,
                "confirmed_events": [],
                "llm_inferred_events": [],
                "final_events": [],
                "risk_adjustment": 0.0,
                "action_plan": None,
                "gate_decision": None,
                "gate_reason": None,
                "dispatch_timestamp": None,
                "outreach_id": None,
            }

            result = await self.graph.ainvoke(initial_state)

            logger.info(
                f"CompassConsumer: Completed {customer_id} — "
                f"events={[e['event_type'] for e in result.get('final_events', [])]} "
                f"gate={result.get('gate_decision')} "
                f"channel={result.get('action_plan', {}).get('channel')}"
            )

        except Exception as e:
            logger.error(
                f"CompassConsumer: Failed to process message "
                f"customer={alarm.get('customer_id', 'unknown')}: {e}",
                exc_info=True,
            )
