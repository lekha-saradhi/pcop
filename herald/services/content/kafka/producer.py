import os
import logging
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

_producer: Producer | None = None


def get_kafka_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "acks": "all",
            "retries": 3,
            "linger.ms": 5,
        })
        logger.info("HERALD: Kafka producer created")
    return _producer
