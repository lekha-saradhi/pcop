import pytest
from unittest.mock import AsyncMock, patch
from ..nodes.verify import verify_node


def _signal(signal_type, confidence, detected=True, evidence=None):
    return {
        "signal_type": signal_type,
        "detected": detected,
        "confidence": confidence,
        "evidence": evidence or [],
        "direction": None,
        "onset_estimate": "2024-10-01",
    }


def _base_state(signals, inferred=None):
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": "HIGH",
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": signals,
        "risk_tier": "high",
        "final_score": 0.75,
        "action_score": 0.45,
        "confirmed_events": [],
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
async def test_verify_confirms_high_confidence_salary():
    state = _base_state([_signal("cusum_salary", 0.85)])

    with patch("services.orchestration.nodes.verify.write_life_event_tool") as mock_tool:
        mock_tool.ainvoke = AsyncMock(return_value={"success": True})
        result = await verify_node(state)

    assert len(result["confirmed_events"]) == 1
    assert result["confirmed_events"][0]["event_type"] == "salary_change"


@pytest.mark.asyncio
async def test_verify_skips_low_confidence():
    state = _base_state([_signal("cusum_salary", 0.75)])

    result = await verify_node(state)
    assert result["confirmed_events"] == []


@pytest.mark.asyncio
async def test_verify_skips_unmapped_signal():
    state = _base_state([_signal("nexus_correlation", 0.90)])
    result = await verify_node(state)
    assert result["confirmed_events"] == []


@pytest.mark.asyncio
async def test_verify_skips_already_inferred():
    inferred = [{"event_type": "salary_change", "confidence": 0.75,
                 "evidence": [], "source": "llm_cognition", "risk_adjustment": 0.05}]
    state = _base_state([_signal("cusum_salary", 0.85)], inferred=inferred)

    result = await verify_node(state)
    assert result["confirmed_events"] == []


@pytest.mark.asyncio
async def test_verify_confirms_bereavement():
    state = _base_state([_signal("lifecycle_mcc_bereavement", 0.95,
                                 evidence=["MCC 7261 funeral"])])

    with patch("services.orchestration.nodes.verify.write_life_event_tool") as mock_tool:
        mock_tool.ainvoke = AsyncMock(return_value={"success": True})
        result = await verify_node(state)

    assert result["confirmed_events"][0]["event_type"] == "bereavement"
