import pytest
from datetime import date
from ..state import CompassState


@pytest.fixture
def base_state() -> CompassState:
    return {
        "customer_id": "C-00000001",
        "as_of_date": str(date.today()),
        "alarm_severity": "HIGH",
        "alarm_timestamp": f"{date.today()}T06:00:00Z",
        "signal_results": [],
        "risk_tier": "high",
        "final_score": 0.75,
        "action_score": 0.45,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": {
            "channel": "email",
            "offer_code": "MA_RATE_UPGRADE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Test plan",
            "suppressed": False,
        },
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.fixture
def critical_state(base_state) -> CompassState:
    return {**base_state, "final_score": 0.95, "risk_tier": "critical", "alarm_severity": "CRITICAL"}


@pytest.fixture
def watch_state(base_state) -> CompassState:
    return {
        **base_state,
        "risk_tier": "watch",
        "final_score": 0.15,
        "alarm_severity": "LOW",
        "action_plan": {"channel": None, "offer_code": None, "timing": None,
                        "owner_id": "system", "priority": 5,
                        "rationale": "Monitor only", "suppressed": False},
    }
