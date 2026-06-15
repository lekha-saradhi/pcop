import os
from confluent_kafka import Producer

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
    return _producer
