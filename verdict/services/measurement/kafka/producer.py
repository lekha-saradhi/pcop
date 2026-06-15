import os
import logging
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

_producer = None


def get_kafka_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "acks": "all",
        })
    return _producer
