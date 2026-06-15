"""SENTINEL — Event-driven real-time re-scorer for high-risk customers."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

TRIGGER_EVENTS = {"ACCOUNT_CLOSURE_REQUEST"}
HIGH_TIER_SCORES_THRESHOLD = 0.80
LATENCY_TARGET_MS = 50

KAFKA_TOPICS = ["pcop.alarms.v1", "pcop.account_events.v1"]
CONSUMER_GROUP = "chronos-sentinel"

_LATENCY_BUCKETS: list[float] = []


@dataclass
class ScoringResult:
    customer_id: str
    churn_prob: float
    attention_weights: list[float]
    latency_ms: float
    triggered_by: str


def _record_latency(ms: float) -> None:
    _LATENCY_BUCKETS.append(ms)
    if len(_LATENCY_BUCKETS) > 10_000:
        _LATENCY_BUCKETS.pop(0)


def _should_trigger(event: dict[str, Any], current_score: float | None, is_high_tier: bool) -> bool:
    """Evaluate whether an event warrants a real-time re-score."""
    event_type = event.get("event_type", "")
    if event_type in TRIGGER_EVENTS:
        return True
    if event.get("bocpd_fired", False):
        return True
    if current_score is not None and current_score >= HIGH_TIER_SCORES_THRESHOLD:
        return True
    if is_high_tier:
        return True
    return False


class SENTINELRealTimeScorer:
    """Kafka consumer that re-scores customers on trigger events."""

    def __init__(
        self,
        onnx_path: str | None = None,
        redis_url: str = "redis://localhost:6379",
        db_url: str | None = None,
        kafka_brokers: str = "localhost:9092",
    ) -> None:
        from services.scoring.serving.onnx_runtime import TARERuntimeSession

        self._onnx = TARERuntimeSession(onnx_path) if onnx_path else None
        self._redis_url = redis_url
        self._db_url = db_url
        self._kafka_brokers = kafka_brokers
        self._redis_client = None
        self._db_conn = None

    def _get_redis(self) -> Any:
        if self._redis_client is None:
            import redis
            self._redis_client = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis_client

    def _get_features_from_cache(self, customer_id: str) -> dict | None:
        """Read customer features from Redis; fall back to DB on cache miss."""
        try:
            r = self._get_redis()
            raw = r.get(f"feat:{customer_id}")
            if raw:
                return json.loads(raw)
        except Exception:
            logger.warning("Redis failure for customer_id=%s — falling back to DB", customer_id)

        # Circuit breaker: read from DB
        return self._get_features_from_db(customer_id)

    def _get_features_from_db(self, customer_id: str) -> dict | None:
        logger.info("Fetching features from DB for customer_id=%s", customer_id)
        return None  # DB fetch implementation goes here

    def score_customer(self, customer_id: str, triggered_by: str) -> ScoringResult | None:
        """Score a single customer and write result to DB.

        Args:
            customer_id: Customer to re-score.
            triggered_by: Description of the triggering event.

        Returns:
            ScoringResult or None if features unavailable.
        """
        t_start = time.perf_counter()

        features = self._get_features_from_cache(customer_id)
        if features is None:
            logger.error("No features available for customer_id=%s", customer_id)
            return None

        token_ids = features.get("token_ids", [0] * 180)
        time_gaps = features.get("time_gaps", [0.0] * 180)

        if self._onnx is None:
            logger.error("ONNX session not initialised")
            return None

        churn_prob, attn_weights = self._onnx.score_single(token_ids, time_gaps)
        latency_ms = (time.perf_counter() - t_start) * 1000

        _record_latency(latency_ms)
        if latency_ms > LATENCY_TARGET_MS:
            logger.warning("Latency SLO breach: customer_id=%s %.1fms > %dms", customer_id, latency_ms, LATENCY_TARGET_MS)

        logger.info(
            "customer_id=%s churn_prob=%.4f latency_ms=%.1f triggered_by=%s",
            customer_id, churn_prob, latency_ms, triggered_by,
        )

        result = ScoringResult(
            customer_id=customer_id,
            churn_prob=churn_prob,
            attention_weights=attn_weights,
            latency_ms=latency_ms,
            triggered_by=triggered_by,
        )
        self._write_result(result)
        return result

    def _write_result(self, result: ScoringResult) -> None:
        """Persist score to churn_scores table (implementation via SQLAlchemy)."""
        logger.debug("Writing score for customer_id=%s to DB", result.customer_id)

    def process_event(self, event: dict[str, Any]) -> None:
        """Handle a single Kafka event."""
        customer_id = event.get("customer_id")
        if not customer_id:
            return

        current_score = event.get("current_churn_score")
        is_high_tier = event.get("risk_tier") == "High"

        if _should_trigger(event, current_score, is_high_tier):
            self.score_customer(customer_id, triggered_by=event.get("event_type", "unknown"))

    def run(self) -> None:
        """Start Kafka consumer loop (blocking)."""
        from kafka import KafkaConsumer  # type: ignore[import]

        consumer = KafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=self._kafka_brokers,
            group_id=CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        logger.info("SENTINEL consumer started on topics %s", KAFKA_TOPICS)

        for message in consumer:
            try:
                self.process_event(message.value)
            except Exception:
                logger.exception("Error processing Kafka message: %s", message)

    @staticmethod
    def latency_percentiles() -> dict[str, float]:
        """Return p50/p95/p99 latency in milliseconds."""
        if not _LATENCY_BUCKETS:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        import numpy as np
        arr = np.array(_LATENCY_BUCKETS)
        return {
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
        }
