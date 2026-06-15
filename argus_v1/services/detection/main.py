"""
Layer 2 Detection Service - entrypoint.

Subscribes to all Kafka topics and dispatches canonical events to the
appropriate agents. Each agent returns at most one SignalResult; all are
fanned out via the CompositeSink (PostgreSQL + Kafka + Redis pub/sub).

Run:
    python -m services.detection.main
"""
import json
import logging
import os
import signal as os_signal
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .agents import (
    SalaryAgent, LocationAgent, ComplaintSentimentAgent, ComplaintVolumeAgent,
    EngagementAgent, TransactionDriftAgent, StressAgent, LifecycleAgent,
    FeatureUsageAgent,
)
from .common.base_agent import BaseAgent, BaselineProvider
from .common.schemas import CanonicalEvent, Baseline
from .common.state_store import InMemoryStateStore, StateStore
from .db.signal_repository import (
    SignalRepository, KafkaAlarmPublisher, RedisPubSubPublisher, CompositeSink,
)
from .joint_detector.bocpd_joint import BocpdJointDetector

log = logging.getLogger(__name__)


TOPIC_TO_AGENT_TYPES = {
    "pcop.salary_credits.v1":    ["salary"],
    "pcop.transactions.v1":      ["location", "transaction_freq", "stress", "lifecycle"],
    "pcop.crm_notes.v1":         ["complaint_sentiment"],
    "pcop.complaints.v1":        ["complaint_volume"],
    "pcop.app_events.v1":        ["engagement", "feature_usage"],
    "pcop.account_events.v1":    ["lifecycle"],
}


@dataclass
class DetectionService:
    agents: dict[str, BaseAgent]
    joint: BocpdJointDetector
    consumer: any   # Kafka consumer; left untyped to keep this importable without kafka
    sink: CompositeSink

    def run(self) -> None:
        log.info("Detection service starting, %d agents registered", len(self.agents))
        for raw_msg in self.consumer:
            try:
                topic = raw_msg.topic
                payload = json.loads(raw_msg.value)
                event = CanonicalEvent.model_validate(payload)
                for agent_type in TOPIC_TO_AGENT_TYPES.get(topic, []):
                    agent = self.agents.get(agent_type)
                    if agent is None:
                        continue
                    agent.handle(event)
            except Exception:
                log.exception("Failed to process message")


def build_default_agents(state_store, baselines: BaselineProvider,
                         sink) -> tuple[dict[str, BaseAgent], BocpdJointDetector]:
    agents = {
        "salary":              SalaryAgent(state_store, baselines, sink, publish_only_alarms=True),
        "location":            LocationAgent(state_store, baselines, sink, publish_only_alarms=True),
        "complaint_sentiment": ComplaintSentimentAgent(state_store, baselines, sink, publish_only_alarms=True),
        "complaint_volume":    ComplaintVolumeAgent(state_store, baselines, sink, publish_only_alarms=True),
        "engagement":          EngagementAgent(state_store, baselines, sink, publish_only_alarms=True),
        "transaction_freq":    TransactionDriftAgent(state_store, baselines, sink, publish_only_alarms=True),
        "stress":              StressAgent(state_store, baselines, sink, publish_only_alarms=True),
        "lifecycle":           LifecycleAgent(state_store, baselines, sink, publish_only_alarms=True),
        "feature_usage":       FeatureUsageAgent(state_store, baselines, sink, publish_only_alarms=True),
    }
    joint = BocpdJointDetector(state_store, baselines, sink, publish_only_alarms=True)
    return agents, joint


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    # ---- Real wiring (Kafka + Postgres + Redis); imports guarded ----
    try:
        from kafka import KafkaConsumer, KafkaProducer
        import psycopg2
        import redis
    except ImportError:
        log.warning("Production deps not installed; service will not start. "
                    "Install kafka-python, psycopg2-binary, redis to run.")
        return 1

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    db_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_client = redis.from_url(redis_url, decode_responses=True)
    state_store = StateStore(redis_client)

    conn = psycopg2.connect(db_url) if db_url else None
    producer = KafkaProducer(bootstrap_servers=bootstrap, acks="all", retries=5)

    from .db.signal_repository import SignalRepository
    sinks = []
    if conn:
        sinks.append(SignalRepository(conn))
    sinks.append(KafkaAlarmPublisher(producer))
    sinks.append(RedisPubSubPublisher(redis_client))
    sink = CompositeSink(sinks)

    # Baseline provider: minimal example fetches from PG. Stubbed here.
    from .common.base_agent import DictBaselineProvider
    baselines = DictBaselineProvider({})

    agents, joint = build_default_agents(state_store, baselines, sink)

    consumer = KafkaConsumer(
        *TOPIC_TO_AGENT_TYPES.keys(),
        bootstrap_servers=bootstrap,
        group_id=os.getenv("KAFKA_CONSUMER_GROUP", "pcop-detection"),
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )

    service = DetectionService(agents=agents, joint=joint, consumer=consumer, sink=sink)
    service.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
