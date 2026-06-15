"""
Base detection agent.

Each agent:
  - consumes one (or more) canonical event types
  - loads/updates per-customer state via StateStore
  - emits at most one SignalResult per event

Concrete agents implement `process_event()`. The base class handles:
  - signal_type identifier
  - alarm publishing (sink)
  - boilerplate result construction
"""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Protocol

from .schemas import CanonicalEvent, SignalResult, AlarmMessage, Baseline
from .state_store import StateStore, InMemoryStateStore


class AlarmSink(Protocol):
    """Anything that can accept emitted alarms (Kafka producer, DB writer, list, ...)."""
    def publish(self, signal: SignalResult) -> None: ...


class ListSink:
    """Test sink that captures alarms in memory."""
    def __init__(self):
        self.alarms: list[SignalResult] = []

    def publish(self, signal: SignalResult) -> None:
        self.alarms.append(signal)


class BaselineProvider(Protocol):
    """Anything that can return a Baseline for (customer_id, signal_name)."""
    def get(self, customer_id: str, signal_name: str) -> Optional[Baseline]: ...


class DictBaselineProvider:
    """Test baseline provider backed by a nested dict."""
    def __init__(self, data: dict[str, dict[str, Baseline]]):
        self._data = data

    def get(self, customer_id: str, signal_name: str) -> Optional[Baseline]:
        return self._data.get(customer_id, {}).get(signal_name)


class BaseAgent(ABC):
    signal_type: str = "base"
    method_used: str = "base"

    def __init__(self, state_store: StateStore | InMemoryStateStore,
                 baselines: BaselineProvider, sink: AlarmSink,
                 publish_only_alarms: bool = False):
        self.state_store = state_store
        self.baselines = baselines
        self.sink = sink
        self.publish_only_alarms = publish_only_alarms

    @abstractmethod
    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        """Process one event, return SignalResult or None if no judgement made."""

    def handle(self, event: CanonicalEvent) -> Optional[SignalResult]:
        result = self.process_event(event)
        if result is None:
            return None
        if result.detected or not self.publish_only_alarms:
            self.sink.publish(result)
        return result

    def _make_result(self, customer_id: str, detected: bool, confidence: float,
                     evidence: list[str], raw_data: dict,
                     cusum_value: Optional[float] = None,
                     alarm_threshold: Optional[float] = None,
                     evaluated_at: Optional[datetime] = None) -> SignalResult:
        return SignalResult(
            customer_id=customer_id,
            signal_type=self.signal_type,
            detected=detected,
            confidence=round(float(confidence), 3),
            evidence=evidence,
            raw_data=raw_data,
            cusum_value=cusum_value,
            alarm_threshold=alarm_threshold,
            method_used=self.method_used,
            evaluated_at=evaluated_at or datetime.now(timezone.utc),
        )


def signal_result_to_alarm(sig: SignalResult) -> AlarmMessage:
    """Translate a SignalResult into the Kafka alarm message envelope."""
    return AlarmMessage(
        alarm_id=str(uuid.uuid4()),
        customer_id=sig.customer_id,
        signal_type=sig.signal_type,
        method_used=sig.method_used,
        detected=sig.detected,
        confidence=sig.confidence,
        cusum_value=sig.cusum_value,
        alarm_threshold=sig.alarm_threshold,
        evidence=sig.evidence,
        raw_data=sig.raw_data,
        evaluated_at=sig.evaluated_at,
    )
