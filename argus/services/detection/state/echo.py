"""ECHO — Signal Expiry & State Manager (2F).

Enforces TTL per signal type, manages signal lifecycle, and publishes
alarm payloads to Kafka (pcop.alarms.v1).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# TTL in days per signal type (spec section 2F)
SIGNAL_TTL_DAYS: dict[str, int] = {
    "sr_transaction":        21,
    "sa_ewma_recency":        7,
    "cusum_salary":          60,
    "beta_cusum_sentiment":  30,
    "ewma_engagement":       14,
    "cfsi_stress":           14,
    "location_rule":         90,
    "lifecycle_mcc":         30,
    "nexus_correlation":     14,
    "oracle_multivariate":    7,
    "rci_market":             1,
}


def signal_expires_at(signal_type: str, evaluated_at: datetime) -> datetime:
    """Return the expiry timestamp for a given signal type."""
    ttl = SIGNAL_TTL_DAYS.get(signal_type, 7)
    return evaluated_at + timedelta(days=ttl)


def is_signal_expired(signal_type: str, evaluated_at: datetime) -> bool:
    """True if the signal has exceeded its TTL."""
    now = datetime.now(tz=timezone.utc)
    return now >= signal_expires_at(signal_type, evaluated_at)


@dataclass
class AlarmPayload:
    customer_id: str
    alarm_timestamp: str          # ISO-8601
    alarm_severity: str           # CRITICAL | HIGH | MEDIUM | LOW
    rejected_tests: list[str]
    fdr_adjusted_p_values: dict[str, float]
    signal_details: dict[str, Any]
    nexus_structure_changed: bool
    oracle_onset_estimate: str | None  # ISO date or None
    active_signal_count: int
    expires_at: str               # ISO-8601


def build_alarm_payload(
    customer_id: str,
    severity: str,
    rejected_tests: list[str],
    adjusted_p: dict[str, float],
    signal_details: dict[str, Any],
    nexus_changed: bool,
    oracle_onset: date | None,
    active_signal_count: int,
    now: datetime | None = None,
) -> AlarmPayload:
    """Construct the standardised alarm payload for Kafka publication."""
    now = now or datetime.now(tz=timezone.utc)
    # Expiry = max TTL across rejected tests
    max_ttl = max(
        (SIGNAL_TTL_DAYS.get(t, 7) for t in rejected_tests),
        default=7,
    )
    expires = now + timedelta(days=max_ttl)

    return AlarmPayload(
        customer_id=customer_id,
        alarm_timestamp=now.isoformat(),
        alarm_severity=severity,
        rejected_tests=rejected_tests,
        fdr_adjusted_p_values=adjusted_p,
        signal_details=signal_details,
        nexus_structure_changed=nexus_changed,
        oracle_onset_estimate=oracle_onset.isoformat() if oracle_onset else None,
        active_signal_count=active_signal_count,
        expires_at=expires.isoformat(),
    )


class ECHOPublisher:
    """Kafka publisher for alarm payloads.

    Falls back to logging if kafka-python is not installed or unavailable.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "pcop.alarms.v1") -> None:
        self._topic = topic
        self._producer: Any = None
        try:
            from kafka import KafkaProducer  # type: ignore[import]
            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            logger.info("ECHO: Kafka producer connected to %s", bootstrap_servers)
        except Exception as exc:
            logger.warning("ECHO: Kafka unavailable, using log sink (%s)", exc)

    def publish(self, payload: AlarmPayload) -> None:
        """Publish alarm payload to Kafka topic (or log if unavailable)."""
        data = asdict(payload)
        if self._producer is not None:
            try:
                self._producer.send(self._topic, data)
                self._producer.flush()
                logger.debug("ECHO: published alarm for %s", payload.customer_id)
                return
            except Exception as exc:
                logger.error("ECHO: Kafka publish failed: %s", exc)
        logger.info("ECHO [alarm]: %s", json.dumps(data))
