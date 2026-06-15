import pytest
from ..nodes.merge import merge_node
from ..state import CompassState


def _base(confirmed=None, inferred=None) -> CompassState:
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": "HIGH",
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": [],
        "risk_tier": "high",
        "final_score": 0.75,
        "action_score": 0.45,
        "confirmed_events": confirmed or [],
        "llm_inferred_events": inferred or [],
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": None,
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_merge_deduplicates_same_event_type():
    confirmed = [{"event_type": "relocation", "confidence": 0.82,
                  "evidence": ["location rule"], "source": "rule_verify",
                  "risk_adjustment": 0.10}]
    inferred = [{"event_type": "relocation", "confidence": 0.91,
                 "evidence": ["llm"], "source": "llm_cognition",
                 "risk_adjustment": 0.10}]

    result = await merge_node(_base(confirmed=confirmed, inferred=inferred))

    events = result["final_events"]
    assert len(events) == 1
    assert events[0]["confidence"] == 0.91


@pytest.mark.asyncio
async def test_merge_keeps_both_different_event_types():
    confirmed = [{"event_type": "relocation", "confidence": 0.85,
                  "evidence": [], "source": "rule_verify", "risk_adjustment": 0.10}]
    inferred = [{"event_type": "financial_stress", "confidence": 0.72,
                 "evidence": [], "source": "llm_cognition", "risk_adjustment": 0.20}]

    result = await merge_node(_base(confirmed=confirmed, inferred=inferred))
    assert len(result["final_events"]) == 2


@pytest.mark.asyncio
async def test_merge_clamps_adjustment():
    events = [
        {"event_type": "financial_stress", "confidence": 0.9,
         "evidence": [], "source": "rule_verify", "risk_adjustment": 0.20},
        {"event_type": "churn_intent", "confidence": 0.8,
         "evidence": [], "source": "rule_verify", "risk_adjustment": 0.25},
    ]
    result = await merge_node(_base(confirmed=events))
    assert result["risk_adjustment"] == pytest.approx(0.30)


@pytest.mark.asyncio
async def test_merge_no_events():
    result = await merge_node(_base())
    assert result["final_events"] == []
    assert result["risk_adjustment"] == 0.0
