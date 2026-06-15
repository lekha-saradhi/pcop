"""
Lifecycle Agent.

Consumes:    pcop.transactions.v1 + pcop.account_events.v1
Method:      Deterministic whitelist of MCC codes / event types.

Detected lifecycle events:
    marriage, new_baby, home_purchase, bereavement, retirement,
    relocation_intl  (these enrich Layer 4 reasoning, not always alarms).
"""
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult


# (mcc, event_label, confidence_bump)
MCC_LIFECYCLE_MAP = {
    "5944": ("marriage", 0.55),          # jewellery
    "7011": ("marriage", 0.30),          # hotels (low alone)
    "5947": ("marriage", 0.30),          # gift / novelty
    "7296": ("marriage", 0.35),          # clothing rental
    "5641": ("new_baby", 0.60),          # children's clothing
    "5999": ("new_baby", 0.45),
    "8099": ("new_baby", 0.45),
    "6552": ("home_purchase", 0.55),     # real estate developers
    "7389": ("home_purchase", 0.40),
    "8111": ("home_purchase", 0.30),     # also bereavement
    "7261": ("bereavement", 0.70),       # funeral services
    "5912": ("bereavement", 0.30),       # pharmacies (weak)
    "6099": ("relocation_intl", 0.40),   # money transfer / remittance
}

ACCOUNT_EVENT_MAP = {
    "JOINT_ACCOUNT_OPEN": ("marriage", 0.55),
    "MORTGAGE_ENQUIRY": ("home_purchase", 0.65),
    "LIFE_INSURANCE_OPEN": ("new_baby", 0.40),
    "WILL_SERVICE_ENQUIRY": ("bereavement", 0.50),
    "RETIREMENT_PLAN_OPEN": ("retirement", 0.70),
}


class LifecycleAgent(BaseAgent):
    signal_type = "lifecycle"
    method_used = "sql_rule"

    EVIDENCE_WINDOW_DAYS = 60

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        customer_id = event.customer_id
        ts = event.event_timestamp

        # Pull aggregated state per lifecycle label
        state = self.state_store.get("lifecycle", customer_id, "agg") or {}
        labels: dict[str, dict] = state.get("labels", {})

        hit_label: Optional[str] = None
        bump = 0.0
        evidence_str = ""

        if event.event_type == "transaction":
            mcc = str(event.payload.get("mcc_code") or "")
            if mcc in MCC_LIFECYCLE_MAP:
                hit_label, bump = MCC_LIFECYCLE_MAP[mcc]
                merchant = event.payload.get("merchant_name") or "merchant"
                evidence_str = (f"MCC {mcc} ({merchant}) suggestive of {hit_label}")
        elif event.event_type == "account_event":
            et = event.payload.get("event_type", "")
            if et in ACCOUNT_EVENT_MAP:
                hit_label, bump = ACCOUNT_EVENT_MAP[et]
                evidence_str = f"Account event {et} -> {hit_label}"

        if not hit_label:
            return None

        # Accumulate evidence for that label
        ldata = labels.get(hit_label, {"confidence": 0.0, "evidence": [], "first_ts": ts.isoformat()})
        ldata["confidence"] = min(1.0, ldata["confidence"] + bump)
        ldata["evidence"] = (ldata["evidence"] + [evidence_str])[-5:]
        ldata["last_ts"] = ts.isoformat()
        labels[hit_label] = ldata

        state["labels"] = labels
        self.state_store.set("lifecycle", customer_id, "agg", state)

        # Fire only when the label's confidence crosses 0.60
        if ldata["confidence"] < 0.60:
            return None

        raw = {
            "lifecycle_label": hit_label,
            "all_label_confidences": {k: round(v["confidence"], 3) for k, v in labels.items()},
            "evidence_count": len(ldata["evidence"]),
        }
        return self._make_result(
            customer_id=customer_id, detected=True, confidence=ldata["confidence"],
            evidence=ldata["evidence"], raw_data=raw,
            evaluated_at=ts,
        )
