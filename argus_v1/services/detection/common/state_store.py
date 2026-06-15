"""
Redis-backed state store for streaming statistical methods.
All per-customer, per-signal state lives here so agents are stateless processes.
"""
import json
from typing import Any, Optional


class StateStore:
    """Wraps Redis for CUSUM, EWMA, SPRT, Page-Hinkley, BOCPD state."""

    def __init__(self, redis_client):
        self.r = redis_client

    @staticmethod
    def _key(method: str, customer_id: str, signal: str) -> str:
        return f"{method}:{customer_id}:{signal}"

    def get(self, method: str, customer_id: str, signal: str) -> Optional[dict]:
        raw = self.r.get(self._key(method, customer_id, signal))
        return json.loads(raw) if raw else None

    def set(self, method: str, customer_id: str, signal: str, state: dict, ttl: int = 86400 * 90):
        self.r.set(self._key(method, customer_id, signal), json.dumps(state), ex=ttl)

    def reset(self, method: str, customer_id: str, signal: str):
        self.r.delete(self._key(method, customer_id, signal))


class InMemoryStateStore:
    """Drop-in fake for local testing without Redis."""

    def __init__(self):
        self._data: dict[str, dict] = {}

    @staticmethod
    def _key(method: str, customer_id: str, signal: str) -> str:
        return f"{method}:{customer_id}:{signal}"

    def get(self, method: str, customer_id: str, signal: str) -> Optional[dict]:
        return self._data.get(self._key(method, customer_id, signal))

    def set(self, method: str, customer_id: str, signal: str, state: dict, ttl: int = 0):
        self._data[self._key(method, customer_id, signal)] = state

    def reset(self, method: str, customer_id: str, signal: str):
        self._data.pop(self._key(method, customer_id, signal), None)
