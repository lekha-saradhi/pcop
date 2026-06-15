import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.compass_nba import compass_nba_node, _fallback_action_plan


def _base_state(risk_tier="high", final_score=0.75, events=None):
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": "HIGH",
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": [],
        "risk_tier": risk_tier,
        "final_score": final_score,
        "action_score": 0.45,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": events or [],
        "risk_adjustment": 0.0,
        "action_plan": None,
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_monitor_plan_for_watch_tier_no_events():
    state = _base_state(risk_tier="watch", final_score=0.15)
    state["alarm_severity"] = "LOW"
    result = await compass_nba_node(state)
    assert result["action_plan"]["channel"] is None
    assert result["action_plan"]["priority"] == 5


@pytest.mark.asyncio
async def test_fallback_plan_critical_tier():
    state = _base_state(risk_tier="critical", final_score=0.88)
    plan = _fallback_action_plan(state)
    assert plan["channel"] == "call"
    assert plan["priority"] == 1


@pytest.mark.asyncio
async def test_fallback_plan_high_tier():
    state = _base_state(risk_tier="high", final_score=0.70)
    plan = _fallback_action_plan(state)
    assert plan["channel"] == "email"
    assert plan["priority"] == 2


@pytest.mark.asyncio
async def test_compass_uses_llm_action_plan():
    state = _base_state(
        risk_tier="high",
        events=[{"event_type": "bereavement", "confidence": 0.95,
                 "evidence": [], "source": "rule_verify", "risk_adjustment": 0.15}],
    )

    plan_result = {
        "channel": "rm_visit",
        "offer_code": "HNW_RM_PRIORITY",
        "timing": "2024-11-02T09:00:00",
        "owner_id": "RM001",
        "priority": 1,
        "rationale": "Bereavement detected, sensitive RM visit needed.",
        "suppressed": False,
    }

    write_call = MagicMock()
    write_call.name = "write_action_plan_tool"
    write_call.args = {k: v for k, v in plan_result.items() if k != "suppressed"}
    write_call.id = "call-001"

    llm_with_tools = MagicMock()
    llm_with_tools.ainvoke = AsyncMock(side_effect=[
        MagicMock(tool_calls=[write_call]),
        MagicMock(tool_calls=[]),
    ])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = llm_with_tools

    with patch("services.orchestration.nodes.compass_nba.get_langchain_compass_llm",
               return_value=mock_llm), \
         patch.object(
             __import__("services.orchestration.tools.db_writes",
                        fromlist=["write_action_plan_tool"]).write_action_plan_tool,
             "ainvoke",
             AsyncMock(return_value={"success": True, "action_plan": plan_result}),
         ):
        result = await compass_nba_node(state)

    assert result["action_plan"]["channel"] == "rm_visit"
