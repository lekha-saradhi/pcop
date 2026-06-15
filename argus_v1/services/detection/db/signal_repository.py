"""
Persistence + Kafka publishing for signal results.

Two sinks combined into one composite sink:
    1. SignalRepository  -> inserts into PostgreSQL `signal_results` table
    2. KafkaAlarmPublisher -> publishes to `pcop.alarms.v1` topic
    3. RedisPubSubPublisher -> publishes to `pcop:alarms` channel for live dashboard
"""
import json
import logging
from datetime import datetime
from typing import Any, Optional

from ..common.base_agent import signal_result_to_alarm
from ..common.schemas import SignalResult

log = logging.getLogger(__name__)


class SignalRepository:
    """Inserts into PostgreSQL signal_results table."""

    INSERT_SQL = """
        INSERT INTO signal_results
          (customer_id, signal_type, detected, confidence, evidence,
           raw_data, cusum_value, alarm_threshold, method_used, evaluated_at)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
        RETURNING result_id;
    """

    def __init__(self, conn):
        self.conn = conn

    def publish(self, sig: SignalResult) -> Optional[int]:
        try:
            with self.conn.cursor() as cur:
                cur.execute(self.INSERT_SQL, (
                    sig.customer_id, sig.signal_type, sig.detected, sig.confidence,
                    sig.evidence, json.dumps(sig.raw_data),
                    sig.cusum_value, sig.alarm_threshold,
                    sig.method_used, sig.evaluated_at,
                ))
                row = cur.fetchone()
                self.conn.commit()
                return row[0] if row else None
        except Exception:
            log.exception("Failed to insert signal_result for %s/%s",
                          sig.customer_id, sig.signal_type)
            self.conn.rollback()
            return None


class KafkaAlarmPublisher:
    """Publishes pcop.alarms.v1 envelopes to Kafka."""

    TOPIC = "pcop.alarms.v1"

    def __init__(self, producer):
        self.producer = producer

    def publish(self, sig: SignalResult) -> None:
        if not sig.detected:
            return
        alarm = signal_result_to_alarm(sig)
        try:
            self.producer.send(
                self.TOPIC,
                key=sig.customer_id.encode("utf-8"),
                value=alarm.model_dump_json().encode("utf-8"),
            )
        except Exception:
            log.exception("Kafka publish failed for %s/%s",
                          sig.customer_id, sig.signal_type)


class RedisPubSubPublisher:
    """Pushes severity-tagged alarms to Redis channel `pcop:alarms` for live dashboard."""

    CHANNEL = "pcop:alarms"

    def __init__(self, redis_client, min_confidence: float = 0.65):
        self.r = redis_client
        self.min_confidence = min_confidence

    def publish(self, sig: SignalResult) -> None:
        if not sig.detected or sig.confidence < self.min_confidence:
            return
        severity = "critical" if sig.confidence >= 0.80 else "medium"
        payload = {
            "severity": severity,
            "title": self._title(sig),
            "description": "; ".join(sig.evidence[:2]),
            "affected_customers": 1,
            "customer_id": sig.customer_id,
            "signal_type": sig.signal_type,
            "timestamp": sig.evaluated_at.isoformat(),
        }
        try:
            self.r.publish(self.CHANNEL, json.dumps(payload))
        except Exception:
            log.exception("Redis publish failed")

    @staticmethod
    def _title(sig: SignalResult) -> str:
        return {
            "salary": "Salary employer change",
            "location": "Location change confirmed",
            "complaint_sentiment": "Negative sentiment alarm",
            "complaint_volume": "Complaint volume surge",
            "engagement": "Digital engagement decay",
            "transaction_freq": "Transaction frequency drift",
            "stress": "Financial stress detected",
            "lifecycle": "Lifecycle event detected",
            "feature_usage": "Feature abandonment detected",
            "bocpd_joint": "BOCPD joint changepoint detected",
        }.get(sig.signal_type, sig.signal_type)


class CompositeSink:
    """Fans out one SignalResult to all configured sinks."""

    def __init__(self, sinks: list):
        self.sinks = sinks

    def publish(self, sig: SignalResult) -> None:
        for s in self.sinks:
            try:
                s.publish(sig)
            except Exception:
                log.exception("Sink failed: %s", type(s).__name__)
