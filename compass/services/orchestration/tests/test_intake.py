import pytest
from unittest.mock import AsyncMock, patch
from ..nodes.intake import intake_node


def _base_state(severity="HIGH"):
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": severity,
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": [],
        "risk_tier": None,
        "final_score": None,
        "action_score": None,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": None,
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_intake_populates_score_fields():
    state = _base_state()

    with patch("services.orchestration.nodes.intake.get_churn_score_raw",
               new_callable=AsyncMock,
               return_value={"final_score": 0.82, "risk_tier": "critical",
                             "action_score": 0.51}):
        result = await intake_node(state)

    assert result["risk_tier"] == "critical"
    assert result["final_score"] == pytest.approx(0.82)
    assert result["action_score"] == pytest.approx(0.51)


@pytest.mark.asyncio
async def test_intake_defaults_on_missing_score():
    state = _base_state()

    with patch("services.orchestration.nodes.intake.get_churn_score_raw",
               new_callable=AsyncMock,
               return_value={"final_score": 0.0, "risk_tier": "low",
                             "action_score": 0.0}):
        result = await intake_node(state)

    assert result["risk_tier"] == "low"


@pytest.mark.asyncio
async def test_intake_resets_event_lists():
    state = _base_state()

    with patch("services.orchestration.nodes.intake.get_churn_score_raw",
               new_callable=AsyncMock,
               return_value={"final_score": 0.5, "risk_tier": "medium",
                             "action_score": 0.3}):
        result = await intake_node(state)

    assert result["confirmed_events"] == []
    assert result["llm_inferred_events"] == []
    assert result["final_events"] == []
    assert result["risk_adjustment"] == 0.0
