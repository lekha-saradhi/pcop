"""
Kafka consumer entrypoint for COLLECT node.
Run with: python -m services.measurement.kafka.consumer
"""
from ..nodes.collect import CollectConsumer


def main():
    consumer = CollectConsumer()
    consumer.run()


if __name__ == "__main__":
    main()
