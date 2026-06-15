"""
Location Agent.

Consumes:    pcop.transactions.v1  (uses merchant_city field)
Method:      Deterministic SQL frequency rule (no ML)
Rule:        Fires if a new city accounts for > NEW_CITY_THRESHOLD of
             transactions in the recent window and was NOT the dominant
             city in the prior window.

State tracked in Redis:
    city_counts_30d:   dict[city -> count] in the trailing 30d window
    city_counts_180d:  dict[city -> count] in the trailing 180d window
    last_transition_anchor_txn:  id of the txn that flipped the city
"""
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult


class LocationAgent(BaseAgent):
    signal_type = "location"
    method_used = "sql_rule"

    NEW_CITY_THRESHOLD = 0.60     # >60% of recent window
    MIN_RECENT_TXNS = 5           # need at least this many txns before alarming
    PRIOR_DOMINANT_THRESHOLD = 0.50

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        city = (event.payload.get("merchant_city") or "").strip()
        if not city:
            return None
        # Only count real transactions (not balance enquiries etc.)
        if event.payload.get("direction") not in ("debit", "credit"):
            return None

        customer_id = event.customer_id
        txn_id = event.payload.get("txn_id")
        amount = event.payload.get("amount", 0)
        mcc = event.payload.get("mcc_code")
        ts = event.event_timestamp

        # Pull state
        state = self.state_store.get("location", customer_id, "city") or {}
        recent = state.get("recent_30d", [])         # list of (iso_ts, city)
        long_window = state.get("history_180d", [])  # list of (iso_ts, city)
        anchor_txn = state.get("transition_anchor_txn")

        recent.append((ts.isoformat(), city))
        long_window.append((ts.isoformat(), city))

        # Trim windows
        recent = self._trim(recent, ts, days=30)
        long_window = self._trim(long_window, ts, days=180)

        # Compute distributions
        recent_dist = self._distribution([c for _, c in recent])
        long_dist = self._distribution([c for _, c in long_window])

        prior_dominant = max(long_dist.items(), key=lambda kv: kv[1], default=(None, 0))
        new_dominant = max(recent_dist.items(), key=lambda kv: kv[1], default=(None, 0))

        detected = False
        evidence: list[str] = []
        confidence = 0.0

        if (len(recent) >= self.MIN_RECENT_TXNS
                and new_dominant[0]
                and new_dominant[1] >= self.NEW_CITY_THRESHOLD
                and prior_dominant[0]
                and new_dominant[0] != prior_dominant[0]
                and prior_dominant[1] >= self.PRIOR_DOMINANT_THRESHOLD):
            # Cooldown: don't re-alarm on the same transition.
            last_alarm_new_city = state.get("last_alarm_new_city")
            if last_alarm_new_city == new_dominant[0]:
                self.state_store.set("location", customer_id, "city", {
                    "recent_30d": recent,
                    "history_180d": long_window,
                    "transition_anchor_txn": state.get("transition_anchor_txn"),
                    "last_alarm_new_city": last_alarm_new_city,
                    "last_update": ts.isoformat(),
                })
                return None
            detected = True
            anchor_txn = anchor_txn or txn_id
            evidence = [
                f"New dominant city: {new_dominant[0]} ({new_dominant[1]*100:.0f}% of last 30d transactions)",
                f"Prior dominant city: {prior_dominant[0]} ({prior_dominant[1]*100:.0f}% of 180d window)",
            ]
            # MCC 6552 (real estate) or 7389 (legal) hint adds context
            if mcc in ("6552", "7389") and amount and amount > 50000:
                evidence.append(
                    f"Large real estate transfer detected {ts.date()} "
                    f"(Rs {int(amount)} -> {event.payload.get('merchant_name', '')}, {city})"
                )
            confidence = min(0.50 + (new_dominant[1] - self.NEW_CITY_THRESHOLD) * 1.2, 0.95)

        # Persist trimmed state
        self.state_store.set("location", customer_id, "city", {
            "recent_30d": recent,
            "history_180d": long_window,
            "transition_anchor_txn": anchor_txn if detected else state.get("transition_anchor_txn"),
            "last_alarm_new_city": (new_dominant[0] if detected
                                    else state.get("last_alarm_new_city")),
            "last_update": ts.isoformat(),
        })

        if not detected:
            return None

        raw = {
            "prior_city": prior_dominant[0],
            "prior_city_share_180d": round(prior_dominant[1], 3),
            "new_city": new_dominant[0],
            "new_city_share_30d": round(new_dominant[1], 3),
            "transition_anchor_txn": anchor_txn,
            "transition_date": ts.date().isoformat(),
            "recent_window_txn_count": len(recent),
        }
        return self._make_result(
            customer_id=customer_id, detected=True, confidence=confidence,
            evidence=evidence, raw_data=raw,
            evaluated_at=ts,
        )

    @staticmethod
    def _trim(buf: list, now: datetime, days: int) -> list:
        cutoff = now - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()
        return [(ts, c) for ts, c in buf if ts >= cutoff_iso]

    @staticmethod
    def _distribution(cities: list[str]) -> dict[str, float]:
        if not cities:
            return {}
        total = len(cities)
        out: dict[str, int] = {}
        for c in cities:
            out[c] = out.get(c, 0) + 1
        return {c: cnt / total for c, cnt in out.items()}
